import asyncio
import sys
import types
import unittest
from unittest.mock import patch


fake_curl = types.ModuleType("curl_cffi")
fake_curl.requests = types.SimpleNamespace()
sys.modules.setdefault("curl_cffi", fake_curl)

from backend.services import mail_service, register  # noqa: E402


class RegisterProviderDispatchTest(unittest.TestCase):
    def test_vipmail_provider_uses_vipmail_client(self):
        events = []

        class SentinelVipMailClient:
            def __init__(self, api_key):
                events.append(("vipmail", api_key))

            def create_address_sync(self):
                raise RuntimeError("stop before qwen signup")

        class SentinelGPTMailClient:
            def __init__(self, api_key=""):
                events.append(("gptmail", api_key))

            def create_address_sync(self):
                raise RuntimeError("wrong provider")

        with (
            patch.object(mail_service, "VipMailClient", SentinelVipMailClient),
            patch.object(mail_service, "GPTMailClient", SentinelGPTMailClient),
        ):
            result = register._register_single_account(
                provider="vipmail",
                vipmail_key="AC-test",
                mail_poll_times=1,
            )

        self.assertIsNone(result)
        self.assertEqual(events, [("vipmail", "AC-test")])

    def test_vipmail_without_key_does_not_fall_back_to_gptmail(self):
        events = []

        class SentinelGPTMailClient:
            def __init__(self, api_key=""):
                events.append(("gptmail", api_key))

        with patch.object(mail_service, "GPTMailClient", SentinelGPTMailClient):
            result = register._register_single_account(
                provider="vipmail",
                vipmail_key="",
                mail_poll_times=1,
            )

        self.assertIsNone(result)
        self.assertEqual(events, [])

    def test_gptmail_provider_passes_smartmail_key(self):
        events = []

        class SentinelGPTMailClient:
            def __init__(self, api_key=""):
                events.append(("gptmail", api_key))

            def create_address_sync(self):
                raise RuntimeError("stop before qwen signup")

        with patch.object(mail_service, "GPTMailClient", SentinelGPTMailClient):
            result = register._register_single_account(
                provider="gptmail",
                smartmail_key="SM-test",
                mail_poll_times=1,
            )

        self.assertIsNone(result)
        self.assertEqual(events, [("gptmail", "SM-test")])

    def test_unknown_provider_does_not_fall_back_to_gptmail(self):
        events = []

        class SentinelGPTMailClient:
            def __init__(self, api_key=""):
                events.append(("gptmail", api_key))

        with patch.object(mail_service, "GPTMailClient", SentinelGPTMailClient):
            result = register._register_single_account(
                provider="not-a-provider",
                mail_poll_times=1,
            )

        self.assertIsNone(result)
        self.assertEqual(events, [])

    def test_batch_registration_passes_provider_keys(self):
        calls = []

        class Pool:
            async def add_account(self, **_kwargs):
                raise AssertionError("No account should be added for a failed slot")

        def fake_register_single_account(**kwargs):
            calls.append(kwargs)
            return None

        async def run_case():
            return await register.perform_batch_registration(
                account_pool=Pool(),
                count=1,
                threads=1,
                provider="vipmail",
                vipmail_key="AC-test",
                smartmail_key="SM-test",
                max_retries=1,
            )

        with patch.object(register, "_register_single_account", fake_register_single_account):
            result = asyncio.run(run_case())

        self.assertEqual(result["success"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(calls[0]["provider"], "vipmail")
        self.assertEqual(calls[0]["vipmail_key"], "AC-test")
        self.assertEqual(calls[0]["smartmail_key"], "SM-test")


if __name__ == "__main__":
    unittest.main()
