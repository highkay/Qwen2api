import unittest

from backend.engine.completion import _parse_events_to_text


class CompletionEventParseTest(unittest.TestCase):
    def test_deep_research_phases_are_split_from_final_answer(self):
        events = [
            {"type": "delta", "phase": "ResearchPlanning", "content": "plan;"},
            {"type": "delta", "phase": "ResearchSearching", "content": "search;"},
            {"type": "delta", "phase": "Writing", "content": "answer"},
            {"type": "delta", "phase": "answer", "content": " done", "status": "finished"},
            {"type": "delta", "phase": "answer", "content": " ignored"},
        ]

        answer, reasoning, native_chunks, image_urls = _parse_events_to_text(events)

        self.assertEqual(answer, "answer done")
        self.assertEqual(reasoning, "plan;search;")
        self.assertEqual(native_chunks, {})
        self.assertEqual(image_urls, [])

    def test_native_tool_call_chunks_are_collected(self):
        events = [
            {
                "type": "delta",
                "phase": "tool_call",
                "content": '{"name":"read_file","arguments":"{\\"path\\": "}',
                "extra": {"tool_call_id": "tc_1"},
            },
            {
                "type": "delta",
                "phase": "tool_call",
                "content": '{"arguments":"\\"app.py\\"}"}',
                "extra": {"tool_call_id": "tc_1"},
            },
        ]

        answer, reasoning, native_chunks, image_urls = _parse_events_to_text(events)

        self.assertEqual(answer, "")
        self.assertEqual(reasoning, "")
        self.assertEqual(native_chunks["tc_1"]["name"], "read_file")
        self.assertEqual(native_chunks["tc_1"]["args"], '{"path": "app.py"}')
        self.assertEqual(image_urls, [])


if __name__ == "__main__":
    unittest.main()
