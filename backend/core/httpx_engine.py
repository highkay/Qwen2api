"""
httpx_engine.py -- 用 curl_cffi 直连 Qwen API（Chrome TLS 指纹）
优点：TLS 指纹与真实 Chrome 一致，连接池复用，流式即时透传
"""

import asyncio
import json
import logging

from backend.core.qwen_headers import BASE_URL, qwen_api_headers, qwen_impersonate

log = logging.getLogger("qwen2api.httpx_engine")


class HttpxEngine:
    """Direct curl_cffi engine -- Chrome TLS fingerprint, connection pool reuse."""

    def __init__(self, pool_size: int = 3, base_url: str = BASE_URL):
        self.base_url = base_url
        self._started = False
        self._ready = asyncio.Event()
        self._session = None

    async def start(self):
        self._started = True
        self._ready.set()
        log.info("[HttpxEngine] 已启动（curl_cffi Chrome指纹直连模式）")

    async def stop(self):
        self._started = False
        if self._session:
            await self._session.close()
            self._session = None
        log.info("[HttpxEngine] 已停止")

    def _auth_headers(self, token: str) -> dict:
        return qwen_api_headers(token, extra={"source": "web"})

    async def api_call(self, method: str, path: str, token: str, body: dict = None) -> dict:
        from curl_cffi.requests import AsyncSession
        url = self.base_url + path
        headers = qwen_api_headers(token, content_type="application/json", extra={"source": "web"})
        data = json.dumps(body, ensure_ascii=False).encode() if body else None
        try:
            async with AsyncSession(impersonate=qwen_impersonate(), timeout=30) as client:
                resp = await client.request(method, url, headers=headers, data=data)
            return {"status": resp.status_code, "body": resp.text}
        except Exception as e:
            log.error(f"[HttpxEngine] api_call error: {e}")
            return {"status": 0, "body": str(e)}

    async def fetch_chat(self, token: str, chat_id: str, payload: dict, buffered: bool = False):
        """Stream Qwen SSE via curl_cffi -- 真流式透传。

        关键设计：
        1. Accept-Encoding: identity — 禁用压缩，避免 Brotli/gzip 解压缓冲
           Qwen 默认返回 br 压缩流，解压器需要积累数据块才能释放，导致 answer 阶段
           内容被缓冲后一次性释放。禁用压缩后每个 SSE 事件到达即可立即读取。
        2. aiter_content() — 逐 TCP 包读取，不等待完整行
        3. 手动按换行分割 — 确保每个 SSE 事件立即透传
        """
        from curl_cffi.requests import AsyncSession
        url = self.base_url + f"/api/v2/chat/completions?chat_id={chat_id}"
        headers = qwen_api_headers(token, content_type="application/json", stream=True, extra={"source": "web"})
        body_bytes = json.dumps(payload, ensure_ascii=False).encode()

        try:
            session = AsyncSession(impersonate=qwen_impersonate(), timeout=120)
            try:
                response = await session.post(
                    url, headers=headers, data=body_bytes, stream=True
                )

                if response.status_code != 200:
                    try:
                        body_text = (response.content).decode("utf-8", "replace")[:2000]
                    except Exception:
                        body_text = ""
                    yield {"status": response.status_code, "body": body_text}
                    await session.close()
                    return

                # 逐块读取，手动按换行分割，确保即时透传
                line_buffer = ""
                async for chunk in response.aiter_content():
                    if not chunk:
                        continue
                    text = chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else chunk
                    line_buffer += text
                    while "\n" in line_buffer:
                        line, line_buffer = line_buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        yield {"status": "streamed", "chunk": line + "\n"}

                # 处理残余缓冲区
                if line_buffer.strip():
                    yield {"status": "streamed", "chunk": line_buffer.strip() + "\n"}

            finally:
                try:
                    await session.close()
                except Exception:
                    pass

        except Exception as e:
            log.error(f"[HttpxEngine] fetch_chat error: {e}")
            yield {"status": 0, "body": str(e)}
