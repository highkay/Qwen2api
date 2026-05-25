import unittest

from backend.core import config
from backend.core.qwen_headers import qwen_api_headers, qwen_impersonate


class QwenHeadersTest(unittest.TestCase):
    def setUp(self):
        self._old_chrome = config.settings.QWEN_CHROME_VERSION
        self._old_web_version = config.settings.QWEN_WEB_VERSION
        self._old_bx_v = config.settings.QWEN_BX_V
        self._old_impersonate = config.settings.QWEN_IMPERSONATE

    def tearDown(self):
        config.settings.QWEN_CHROME_VERSION = self._old_chrome
        config.settings.QWEN_WEB_VERSION = self._old_web_version
        config.settings.QWEN_BX_V = self._old_bx_v
        config.settings.QWEN_IMPERSONATE = self._old_impersonate

    def test_headers_are_built_from_runtime_qwen_web_settings(self):
        config.settings.QWEN_CHROME_VERSION = "148"
        config.settings.QWEN_WEB_VERSION = "0.2.57"
        config.settings.QWEN_BX_V = "2.5.36"
        config.settings.QWEN_IMPERSONATE = ""

        headers = qwen_api_headers("token-1", content_type="application/json", stream=True)

        self.assertEqual(qwen_impersonate(), "chrome148")
        self.assertIn("Chrome/148.0.0.0", headers["user-agent"])
        self.assertIn('"Chromium";v="148"', headers["sec-ch-ua"])
        self.assertEqual(headers["version"], "0.2.57")
        self.assertEqual(headers["bx-v"], "2.5.36")
        self.assertEqual(headers["authorization"], "Bearer token-1")
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(headers["accept"], "text/event-stream")
        self.assertEqual(headers["accept-encoding"], "identity")
        self.assertEqual(headers["x-accel-buffering"], "no")


if __name__ == "__main__":
    unittest.main()
