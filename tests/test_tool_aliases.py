import unittest

from backend.services.prompt_builder import messages_to_prompt
from backend.services.tool_parser import build_tool_blocks_from_native_chunks, parse_tool_calls


def _tool_request(messages=None, tool_choice=None):
    request = {
        "messages": messages or [{"role": "user", "content": "List files"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "Bash",
                    "description": "Run a shell command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Command to execute",
                            },
                            "mode": {
                                "type": "string",
                                "enum": ["fast", "safe"],
                                "description": "Execution mode",
                            },
                        },
                        "required": ["command"],
                    },
                },
            }
        ],
    }
    if tool_choice is not None:
        request["tool_choice"] = tool_choice
    return request


class ToolAliasTests(unittest.TestCase):
    def test_prompt_uses_alias_and_compact_schema(self):
        prompt, tools = messages_to_prompt(
            _tool_request(
                tool_choice={"type": "function", "function": {"name": "Bash"}}
            )
        )

        alias = tools[0]["name"]
        self.assertTrue(alias.startswith("u_"))
        self.assertNotIn("Bash", alias)
        self.assertEqual(alias, tools[0]["_qwen_name"])
        self.assertEqual("Bash", tools[0]["_original_name"])
        self.assertIn(f"### {alias}", prompt)
        self.assertNotIn("### Bash", prompt)
        self.assertIn("command: string", prompt)
        self.assertIn('mode?: "fast" | "safe"', prompt)
        self.assertIn(f"exactly this tool alias: `{alias}`", prompt)
        self.assertNotIn('"properties"', prompt)

    def test_parser_maps_alias_back_to_original_name(self):
        _, tools = messages_to_prompt(_tool_request())
        alias = tools[0]["name"]
        blocks, stop_reason = parse_tool_calls(
            f'[TOOL_CALL]\n{{"name": "{alias}", "arguments": {{"command": "pwd"}}}}\n[/TOOL_CALL]',
            tools,
        )

        self.assertEqual("tool_use", stop_reason)
        self.assertEqual("Bash", blocks[0]["name"])
        self.assertEqual({"command": "pwd"}, blocks[0]["input"])

    def test_parser_accepts_original_name_for_backward_compatibility(self):
        _, tools = messages_to_prompt(_tool_request())
        blocks, stop_reason = parse_tool_calls(
            '[TOOL_CALL]\n{"name": "Bash", "arguments": {"command": "pwd"}}\n[/TOOL_CALL]',
            tools,
        )

        self.assertEqual("tool_use", stop_reason)
        self.assertEqual("Bash", blocks[0]["name"])

    def test_native_chunks_map_alias_back_to_original_name(self):
        _, tools = messages_to_prompt(_tool_request())
        alias = tools[0]["name"]
        blocks, stop_reason = build_tool_blocks_from_native_chunks(
            {"tc_1": {"name": alias, "args": '{"command": "pwd"}'}},
            tools,
        )

        self.assertEqual("tool_use", stop_reason)
        self.assertEqual("Bash", blocks[0]["name"])

    def test_history_tool_messages_are_rendered_with_alias(self):
        prompt, tools = messages_to_prompt(
            _tool_request(
                messages=[
                    {"role": "user", "content": "Run pwd"},
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "Bash",
                                    "arguments": '{"command": "pwd"}',
                                },
                            }
                        ],
                    },
                    {
                        "role": "tool",
                        "tool_call_id": "call_1",
                        "name": "Bash",
                        "content": "/repo",
                    },
                ]
            )
        )

        alias = tools[0]["name"]
        self.assertIn(f'"name": "{alias}"', prompt)
        self.assertIn(f'[TOOL_RESULT name="{alias}" id="call_1"]', prompt)


if __name__ == "__main__":
    unittest.main()
