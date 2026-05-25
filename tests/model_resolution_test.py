import unittest

from backend.core import config


class ModelResolutionTest(unittest.TestCase):
    def setUp(self):
        self._old_model_map = dict(config.MODEL_MAP)
        self._old_enable_special = config.settings.ENABLE_SPECIAL_CHAT_MODES
        config.MODEL_MAP.clear()
        config.settings.ENABLE_SPECIAL_CHAT_MODES = True

    def tearDown(self):
        config.MODEL_MAP.clear()
        config.MODEL_MAP.update(self._old_model_map)
        config.settings.ENABLE_SPECIAL_CHAT_MODES = self._old_enable_special

    def test_thinking_suffixes_resolve_to_base_t2t_model(self):
        thinking = config.resolve_model_request("qwen3.6-plus-thinking")
        self.assertEqual(thinking.model, "qwen3.6-plus")
        self.assertEqual(thinking.chat_mode, "t2t")
        self.assertIs(thinking.thinking, True)
        self.assertEqual(thinking.suffix, "-thinking")

        nothinking = config.resolve_model_request("qwen3.6-plus-nothinking")
        self.assertEqual(nothinking.model, "qwen3.6-plus")
        self.assertEqual(nothinking.chat_mode, "t2t")
        self.assertIs(nothinking.thinking, False)
        self.assertEqual(nothinking.suffix, "-nothinking")

    def test_special_mode_suffixes_resolve_to_chat_modes(self):
        cases = {
            "qwen3.6-plus-deep-research": ("qwen3.6-plus", "deep_research", "-deep-research"),
            "qwen3.6-plus-webdev": ("qwen3.6-plus", "web_dev", "-webdev"),
            "qwen3.6-plus-web-dev": ("qwen3.6-plus", "web_dev", "-web-dev"),
            "qwen3.6-plus-slides": ("qwen3.6-plus", "slides", "-slides"),
            "qwen3.6-plus-video": ("qwen3.6-plus", "t2v", "-video"),
            "qwen3.6-plus-t2v": ("qwen3.6-plus", "t2v", "-t2v"),
            "qwen3.6-plus-image": ("qwen3.6-plus", "t2i", "-image"),
            "qwen3.6-plus-t2i": ("qwen3.6-plus", "t2i", "-t2i"),
        }
        for requested, expected in cases.items():
            with self.subTest(requested=requested):
                resolved = config.resolve_model_request(requested)
                self.assertEqual((resolved.model, resolved.chat_mode, resolved.suffix), expected)
                self.assertIsNone(resolved.thinking)

    def test_qwen_image_keeps_model_id_but_uses_t2i_mode(self):
        resolved = config.resolve_model_request("qwen-image")
        self.assertEqual(resolved.model, "qwen-image")
        self.assertEqual(resolved.chat_mode, "t2i")

    def test_qwen37_preview_mapping_forces_thinking(self):
        resolved = config.resolve_model_request("qwen3.7-plus-preview")
        self.assertEqual(resolved.model, "qwen-latest-series-invite-beta-v16")
        self.assertEqual(resolved.chat_mode, "t2t")
        self.assertIs(resolved.thinking, True)

    def test_legacy_helpers_delegate_to_model_resolution(self):
        self.assertEqual(config.resolve_model("qwen3.6-plus-deep-research"), "qwen3.6-plus")
        self.assertIsNone(config.resolve_model_thinking("qwen3.6-plus-deep-research"))
        self.assertIs(config.resolve_model_thinking("qwen3.6-plus-nothinking"), False)


if __name__ == "__main__":
    unittest.main()
