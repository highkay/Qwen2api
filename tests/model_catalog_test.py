import asyncio
import types
import unittest

from backend.services.model_catalog import ModelCatalog, build_openai_model_entries


class ModelCatalogTest(unittest.TestCase):
    def test_build_entries_expands_qwen_capability_suffixes(self):
        raw_models = [
            {
                "info": {
                    "model": "qwen-live",
                    "meta": {
                        "capabilities": {
                            "thinking": True,
                            "deep_research": True,
                            "image_generation": True,
                            "video_generation": True,
                            "web_dev": True,
                            "slides": True,
                        }
                    },
                }
            },
            {"id": ""},
            "not-a-model",
        ]

        entries = build_openai_model_entries(raw_models)
        ids = {entry["id"] for entry in entries}

        self.assertIn("qwen-live", ids)
        self.assertIn("qwen-live-nothinking", ids)
        self.assertIn("qwen-live-thinking", ids)
        self.assertIn("qwen-live-deep-research", ids)
        self.assertIn("qwen-live-image", ids)
        self.assertIn("qwen-live-video", ids)
        self.assertIn("qwen-live-webdev", ids)
        self.assertIn("qwen-live-slides", ids)
        self.assertTrue(all(entry["object"] == "model" for entry in entries))
        self.assertTrue(all(entry["owned_by"] == "qwen" for entry in entries))

    def test_catalog_refreshes_with_account_and_releases_it(self):
        account = types.SimpleNamespace(token="token-1", inflight=1)
        calls = []

        class Pool:
            async def acquire_wait(self, timeout):
                calls.append(("acquire", timeout))
                return account

            def release(self, released_account, tokens_used=0):
                calls.append(("release", released_account, tokens_used))

        class Client:
            account_pool = Pool()

            async def list_models(self, token):
                calls.append(("list_models", token))
                return [{"id": "qwen-live", "capabilities": ["thinking"]}]

        async def run_case():
            catalog = ModelCatalog()
            return await catalog.get_openai_models(Client())

        entries = asyncio.run(run_case())
        ids = {entry["id"] for entry in entries}

        self.assertIn("qwen-live", ids)
        self.assertIn("qwen-live-thinking", ids)
        self.assertEqual(calls[0][0], "acquire")
        self.assertEqual(calls[1], ("list_models", "token-1"))
        self.assertEqual(calls[2], ("release", account, 0))


if __name__ == "__main__":
    unittest.main()
