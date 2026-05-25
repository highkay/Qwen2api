import unittest

from backend.services.qwen_client import QwenClient


class QwenPayloadModesTest(unittest.TestCase):
    def test_deep_research_payload_uses_research_chat_mode(self):
        client = QwenClient(engine=None, account_pool=None)

        payload = client._build_payload(
            "chat-1",
            "qwen3.6-plus",
            "research this",
            chat_mode="deep_research",
        )
        message = payload["messages"][0]
        feature_config = message["feature_config"]

        self.assertEqual(payload["chat_mode"], "deep_research")
        self.assertEqual(message["chat_type"], "deep_research")
        self.assertEqual(message["sub_chat_type"], "deep_research")
        self.assertEqual(message["extra"]["meta"]["subChatType"], "deep_research")
        self.assertEqual(feature_config["research_mode"], "deep")
        self.assertIs(feature_config["auto_search"], True)
        self.assertIs(feature_config["code_interpreter"], True)

    def test_video_payload_disables_text_tools_and_enables_video_generation(self):
        client = QwenClient(engine=None, account_pool=None)

        payload = client._build_payload(
            "chat-1",
            "qwen3.6-plus",
            "make a video",
            thinking=True,
            chat_mode="t2v",
        )
        message = payload["messages"][0]
        feature_config = message["feature_config"]

        self.assertEqual(payload["chat_mode"], "t2v")
        self.assertEqual(message["chat_type"], "t2v")
        self.assertIs(feature_config["thinking_enabled"], False)
        self.assertEqual(feature_config["thinking_mode"], "off")
        self.assertIs(feature_config["auto_search"], False)
        self.assertIs(feature_config["code_interpreter"], False)
        self.assertIs(feature_config["video_generation"], True)


if __name__ == "__main__":
    unittest.main()
