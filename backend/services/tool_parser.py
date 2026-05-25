"""
tool_parser.py -- 工具调用解析与流式防泄漏
从模型输出中解析工具调用，支持：
- [TOOL_CALL]...{...}...[/TOOL_CALL] 括号格式（主格式）
- <tool_call>...</tool_call> XML 格式（兼容旧格式）
- Qwen 原生 tool_call SSE 事件（native FC）

流式防泄漏：
- 代码围栏内的工具标记不触发
- Markdown 行内 code span 内的标记不触发
- 未完成的工具块持续缓冲
"""

import json
import re
import uuid
import logging

log = logging.getLogger("qwen2api.tool_parser")


# ============================================================================
# JSON 修复
# ============================================================================

_UNQUOTED_KEY = re.compile(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:')
_TRAILING_COMMA = re.compile(r',\s*([}\]])')
_SINGLE_QUOTE_SIMPLE = re.compile(r"'([^']*)'")


def repair_json(raw: str) -> str:
    """修复模型输出中常见的 JSON 格式错误。"""
    s = raw.strip()
    if not s:
        return s
    # 单引号 -> 双引号（仅简单情况）
    if "'" in s and '"' not in s:
        s = s.replace("'", '"')
    # 无引号 key -> 加双引号
    s = _UNQUOTED_KEY.sub(r'\1"\2":', s)
    # 尾随逗号
    s = _TRAILING_COMMA.sub(r'\1', s)
    # 非法反斜杠修复
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in ('"', '\\', '/', 'b', 'f', 'n', 'r', 't'):
                result.append(s[i:i+2])
                i += 2
                continue
            elif nxt == 'u' and i + 5 < len(s) and all(c in '0123456789abcdefABCDEF' for c in s[i+2:i+6]):
                result.append(s[i:i+6])
                i += 6
                continue
            else:
                result.append('\\\\')
                i += 1
                continue
        result.append(s[i])
        i += 1
    return ''.join(result)


def _safe_json_loads(raw: str) -> dict | None:
    """先直接解析，失败后修复重试。"""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        return json.loads(repair_json(raw))
    except (json.JSONDecodeError, ValueError):
        pass
    # 最后尝试：提取 JSON 对象部分
    try:
        start = raw.find('{')
        end = raw.rfind('}')
        if start >= 0 and end > start:
            return json.loads(repair_json(raw[start:end+1]))
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# ============================================================================
# 代码围栏保护
# ============================================================================

_CODE_FENCE_PATTERN = re.compile(r'(```+|~~~+)')


def _is_inside_code_fence(text: str, pos: int) -> bool:
    """检查 pos 位置是否在代码围栏内。"""
    # 扫描 pos 之前的所有围栏标记
    prefix = text[:pos]
    fence_stack = []
    for m in _CODE_FENCE_PATTERN.finditer(prefix):
        marker = m.group(1)
        line_start = prefix.rfind('\n', 0, m.start()) + 1
        before_marker = prefix[line_start:m.start()].strip()
        if before_marker:
            continue  # 不在行首，不是围栏
        if not fence_stack:
            fence_stack.append(marker[0] * len(marker))
        elif marker[0] == fence_stack[-1][0] and len(marker) >= len(fence_stack[-1]):
            fence_stack.pop()
        else:
            fence_stack.append(marker[0] * len(marker))
    return len(fence_stack) > 0


def _is_inside_inline_code(text: str, pos: int) -> bool:
    """检查 pos 位置是否在行内代码 span 内。"""
    prefix = text[:pos]
    ticks = 0
    i = 0
    while i < len(prefix):
        if prefix[i] == '`':
            run = 0
            while i + run < len(prefix) and prefix[i + run] == '`':
                run += 1
            if ticks == 0:
                # 检查是否是围栏（行首 3+ 个反引号）
                line_start = prefix.rfind('\n', 0, i) + 1
                if run >= 3 and prefix[line_start:i].strip() == '':
                    i += run
                    continue
                ticks = run
            elif run == ticks:
                ticks = 0
            i += run
        else:
            i += 1
    return ticks > 0


def _strip_code_fences(text: str) -> str:
    """移除代码围栏内容，避免误匹配。"""
    lines = text.split('\n')
    result = []
    in_fence = False
    fence_marker = ""
    for line in lines:
        stripped = line.lstrip()
        if not in_fence:
            m = re.match(r'^(`{3,}|~{3,})', stripped)
            if m:
                in_fence = True
                fence_marker = m.group(1)[0] * len(m.group(1))
                continue
            result.append(line)
        else:
            m = re.match(r'^(`{3,}|~{3,})\s*$', stripped)
            if m and m.group(1)[0] == fence_marker[0] and len(m.group(1)) >= len(fence_marker):
                in_fence = False
                fence_marker = ""
            # 围栏内的内容不加入 result
    return '\n'.join(result)


# ============================================================================
# 工具调用匹配
# ============================================================================

# 主格式：[TOOL_CALL]...{...}...[/TOOL_CALL]
_TOOL_CALL_PATTERN = re.compile(
    r'\[TOOL_CALL\](.*?)\[/TOOL_CALL\]',
    re.DOTALL
)

# 兼容旧格式：<tool_call>...</tool_call>
_TOOL_CALL_XML_PATTERN = re.compile(
    r'<tool_call>(.*?)</tool_call>',
    re.DOTALL
)

# 兼容 function_call 格式
_FUNCTION_CALL_PATTERN = re.compile(
    r'<function_call>(.*?)</function_call>',
    re.DOTALL
)


def parse_tool_calls(text: str, tools: list[dict]) -> tuple[list[dict], str]:
    """
    从模型输出文本中解析工具调用。

    支持多种格式，按优先级：
    1. [TOOL_CALL]...[/TOOL_CALL] (主格式)
    2. <tool_call>...</tool_call> (兼容)
    3. <function_call>...</function_call> (兼容)

    Returns:
        (content_blocks, stop_reason)
        stop_reason: "tool_use" 如果有工具调用，否则 "end_turn"
    """
    if not tools or not text:
        return [], "end_turn"

    tool_names = {t.get("name", "") for t in tools}
    blocks: list[dict] = []

    # 在去除代码围栏后的文本上做匹配
    safe_text = _strip_code_fences(text)

    # 按优先级尝试各种格式
    for pattern in (_TOOL_CALL_PATTERN, _TOOL_CALL_XML_PATTERN, _FUNCTION_CALL_PATTERN):
        for match in pattern.finditer(safe_text):
            # 额外检查：确保匹配位置不在行内代码 span 内
            if _is_inside_inline_code(safe_text, match.start()):
                continue

            raw = match.group(1).strip()
            data = _safe_json_loads(raw)
            if data is None:
                log.debug(f"[ToolParser] JSON 解析失败 | raw={raw[:120]}")
                continue

            name = data.get("name", "")
            inp = data.get("arguments", data.get("input", data.get("params", data.get("parameters", {}))))

            if not name:
                continue

            # 工具名验证：必须在可用工具列表中
            if tool_names and name not in tool_names:
                # 模糊匹配：大小写不敏感
                matched = next((tn for tn in tool_names if tn.lower() == name.lower()), None)
                if matched:
                    name = matched
                else:
                    log.debug(f"[ToolParser] 工具名不在列表中: {name}")
                    continue

            # 参数验证：确保是 dict
            if isinstance(inp, str):
                try:
                    inp = json.loads(inp)
                except (json.JSONDecodeError, ValueError):
                    inp = {"raw": inp}
            if not isinstance(inp, dict):
                inp = {}

            # 空参数检测：对命令类工具，空 command 视为无效
            command_params = {"command", "cmd", "script"}
            for cp in command_params:
                if cp in inp and not str(inp[cp]).strip():
                    log.debug(f"[ToolParser] 空命令参数，跳过: {name}.{cp}")
                    inp = None
                    break
            if inp is None:
                continue

            blocks.append({
                "type": "tool_use",
                "id": f"toolu_{uuid.uuid4().hex[:12]}",
                "name": name,
                "input": inp,
            })

        if blocks:
            break  # 找到就不再尝试其他格式

    if blocks:
        # 提取工具调用之前的文本
        first_match = None
        for pattern in (_TOOL_CALL_PATTERN, _TOOL_CALL_XML_PATTERN, _FUNCTION_CALL_PATTERN):
            m = pattern.search(safe_text)
            if m:
                if first_match is None or m.start() < first_match.start():
                    first_match = m
        prefix = text[:first_match.start()].strip() if first_match else ""
        result = []
        if prefix:
            result.append({"type": "text", "text": prefix})
        result.extend(blocks)
        return result, "tool_use"

    return [], "end_turn"


# ============================================================================
# Native FC 事件解析
# ============================================================================

def build_tool_blocks_from_native_chunks(
    native_tc_chunks: dict, tools: list[dict]
) -> tuple[list[dict], str]:
    """
    从 Qwen 原生 tool_call SSE 事件分片中构建工具块。
    这是 native-first 策略的主路径。
    """
    if not native_tc_chunks:
        return [], "end_turn"

    tool_names = {t.get("name", "") for t in tools} if tools else set()
    blocks: list[dict] = []

    for tc_id, tc in native_tc_chunks.items():
        name = tc.get("name", "")
        args_str = tc.get("args", "")

        if not name:
            continue

        # 工具名验证（含模糊匹配）
        if tool_names and name not in tool_names:
            matched = next((tn for tn in tool_names if tn.lower() == name.lower()), None)
            if matched:
                name = matched
            else:
                log.warning(f"[NativeFC] 原生工具名不在列表中: {name}")
                continue

        # 参数解析
        try:
            inp = json.loads(args_str) if args_str else {}
        except (json.JSONDecodeError, ValueError):
            # 尝试修复
            repaired = _safe_json_loads(args_str)
            if repaired is not None:
                inp = repaired
            else:
                inp = {"raw": args_str}

        if not isinstance(inp, dict):
            inp = {}

        blocks.append({
            "type": "tool_use",
            "id": f"toolu_{uuid.uuid4().hex[:12]}",
            "name": name,
            "input": inp,
        })

    if blocks:
        return blocks, "tool_use"
    return [], "end_turn"


# ============================================================================
# 格式纠正注入
# ============================================================================

def inject_format_reminder(prompt: str, blocked_name: str) -> str:
    """
    当 Qwen 平台拦截了原生工具调用时，注入 XML fallback 格式纠正提示。
    使用注意力优化结构：明确指令 + 正确示例 + 锚点。
    """
    reminder = (
        f"\n\n[SYSTEM NOTICE - TOOL FORMAT CHANGE]\n"
        f"The native tool calling for '{blocked_name}' was blocked by the platform.\n"
        f"You MUST use this alternative format instead:\n\n"
        f"[TOOL_CALL]\n"
        f'{{"name": "{blocked_name}", "arguments": {{...fill actual parameters here...}}}}\n'
        f"[/TOOL_CALL]\n\n"
        f"CRITICAL RULES:\n"
        f"- Use [TOOL_CALL]...[/TOOL_CALL] brackets (NOT XML tags)\n"
        f"- Arguments must be valid JSON with double-quoted keys\n"
        f"- Fill in the actual parameter values, not placeholders\n"
        f"- The tool call block must be the LAST content in your response\n"
        f"- Do NOT apologize or explain. Just output the tool call.\n"
    )

    if prompt.rstrip().endswith("Assistant:"):
        prompt = prompt.rstrip()[:-len("Assistant:")] + reminder + "\nAssistant:"
    else:
        prompt += reminder + "\nAssistant:"

    return prompt


# ============================================================================
# 工具循环检测
# ============================================================================

def should_block_tool_call(
    history_messages: list, tool_name: str, tool_input: dict
) -> tuple[bool, str]:
    """
    检测是否存在重复的工具调用（防止工具循环）。
    检查最近 10 条消息中是否有相同工具+相同参数的调用。
    """
    if not history_messages:
        return False, ""

    recent_calls: list[dict] = []
    checked = 0
    for msg in reversed(history_messages):
        if not isinstance(msg, dict):
            continue
        checked += 1
        if checked > 10:
            break

        tool_calls = msg.get("tool_calls", [])
        for tc in tool_calls:
            func = tc.get("function", {})
            recent_calls.append({
                "name": func.get("name", ""),
                "arguments": func.get("arguments", ""),
            })

    current_args = json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
    duplicate_count = 0
    for rc in recent_calls:
        if rc["name"] == tool_name:
            try:
                rc_args = json.dumps(json.loads(rc["arguments"]), sort_keys=True, ensure_ascii=False)
                if rc_args == current_args:
                    duplicate_count += 1
            except (json.JSONDecodeError, ValueError):
                if rc["arguments"] == current_args:
                    duplicate_count += 1

    if duplicate_count >= 2:
        return True, f"Tool '{tool_name}' called {duplicate_count + 1} times with identical arguments"

    return False, ""


# ============================================================================
# 流式 Tool Sieve（防泄漏状态机）
# ============================================================================

class ToolSieveState:
    """流式工具调用检测状态机，防止原始标记泄漏给客户端。"""

    def __init__(self):
        self.pending = ""          # 待处理缓冲
        self.capture = ""          # 正在捕获的工具块
        self.capturing = False     # 是否处于捕获模式
        self.fence_depth = 0       # 代码围栏嵌套深度
        self.inline_ticks = 0      # 行内代码 span 反引号计数

    def process_chunk(self, chunk: str, tool_names: list[str]) -> list[dict]:
        """
        处理一个 SSE chunk，返回事件列表。
        事件类型：
        - {"type": "text", "content": "..."} -- 安全文本，可直接输出
        - {"type": "tool_calls", "calls": [...]} -- 检测到的工具调用
        """
        if chunk:
            self.pending += chunk

        events = []

        while True:
            if self.capturing:
                # 正在捕获工具块
                self.capture += self.pending
                self.pending = ""

                # 尝试提取完整工具调用
                result = self._try_extract_tool_call(tool_names)
                if result is None:
                    # 未完成，继续等待
                    break
                elif result["type"] == "tool_calls":
                    events.append(result)
                    self.capturing = False
                    self.capture = ""
                elif result["type"] == "text":
                    # 不是工具调用，释放为文本
                    events.append(result)
                    self.capturing = False
                    self.capture = ""
                continue

            # 未在捕获模式：扫描工具标签起始
            if not self.pending:
                break

            start = self._find_tool_start()
            if start == -2:
                # 部分标签，hold 住
                break
            elif start >= 0:
                # 找到工具标签起始
                prefix = self.pending[:start]
                if prefix:
                    events.append({"type": "text", "content": prefix})
                self.capture = self.pending[start:]
                self.pending = ""
                self.capturing = True
                continue
            else:
                # 没有工具标签，安全输出
                safe, hold = self._split_safe(self.pending)
                if safe:
                    events.append({"type": "text", "content": safe})
                    self.pending = hold
                else:
                    break

        return events

    def flush(self, tool_names: list[str]) -> list[dict]:
        """流结束时，处理残留缓冲。"""
        events = self.process_chunk("", tool_names)

        if self.capturing:
            # 尝试最后一次提取
            result = self._try_extract_tool_call(tool_names)
            if result and result["type"] == "tool_calls":
                events.append(result)
            elif self.capture:
                events.append({"type": "text", "content": self.capture})
            self.capturing = False
            self.capture = ""

        if self.pending:
            events.append({"type": "text", "content": self.pending})
            self.pending = ""

        return events

    def _find_tool_start(self) -> int:
        """
        在 pending 中查找工具标签起始位置。
        返回：
        - >= 0: 找到的位置
        - -1: 没找到
        - -2: 有部分标签，需要 hold
        """
        text = self.pending

        # 查找 [TOOL_CALL] 或 <tool_call>
        patterns = [
            ("[TOOL_CALL]", "[TOOL_C"),
            ("<tool_call>", "<tool_c"),
            ("<function_call>", "<function_c"),
        ]

        earliest = -1
        for full, partial in patterns:
            idx = text.find(full)
            if idx >= 0:
                # 检查是否在代码围栏/行内代码内
                if _is_inside_code_fence(text, idx) or _is_inside_inline_code(text, idx):
                    continue
                if earliest < 0 or idx < earliest:
                    earliest = idx

        if earliest >= 0:
            return earliest

        # 检查是否有部分标签在末尾
        for full, partial in patterns:
            for plen in range(len(partial), 0, -1):
                if text.endswith(partial[:plen]):
                    return -2

        return -1

    def _split_safe(self, text: str) -> tuple[str, str]:
        """分割安全输出和需要 hold 的部分。"""
        # 检查末尾是否有部分工具标签
        patterns = ["[TOOL_C", "<tool_c", "<function_c"]
        for partial in patterns:
            for plen in range(len(partial), 0, -1):
                if text.endswith(partial[:plen]):
                    return text[:-plen], text[-plen:]
        return text, ""

    def _try_extract_tool_call(self, tool_names: list[str]) -> dict | None:
        """尝试从 capture 中提取完整工具调用。"""
        text = self.capture

        # 检查是否有完整的闭合标签
        close_patterns = [
            ("[TOOL_CALL]", "[/TOOL_CALL]"),
            ("<tool_call>", "</tool_call>"),
            ("<function_call>", "</function_call>"),
        ]

        for open_tag, close_tag in close_patterns:
            if text.startswith(open_tag):
                close_idx = text.find(close_tag)
                if close_idx < 0:
                    # 没有闭合标签，继续等待
                    return None
                # 提取内容
                inner = text[len(open_tag):close_idx].strip()
                suffix = text[close_idx + len(close_tag):]

                data = _safe_json_loads(inner)
                if data is None:
                    # JSON 解析失败，作为文本释放
                    return {"type": "text", "content": text}

                name = data.get("name", "")
                inp = data.get("arguments", data.get("input", data.get("params", {})))

                if not name:
                    return {"type": "text", "content": text}

                if isinstance(inp, str):
                    try:
                        inp = json.loads(inp)
                    except (json.JSONDecodeError, ValueError):
                        inp = {"raw": inp}
                if not isinstance(inp, dict):
                    inp = {}

                # 如果有后续内容，放回 pending
                if suffix.strip():
                    self.pending = suffix + self.pending

                return {
                    "type": "tool_calls",
                    "calls": [{
                        "type": "tool_use",
                        "id": f"toolu_{uuid.uuid4().hex[:12]}",
                        "name": name,
                        "input": inp,
                    }]
                }

        # 没有匹配的开始标签，释放为文本
        if not any(text.startswith(ot) for ot, _ in close_patterns):
            return {"type": "text", "content": text}

        # 有开始标签但没有结束标签，继续等待
        return None
