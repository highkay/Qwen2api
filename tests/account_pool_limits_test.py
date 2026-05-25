import asyncio
import base64
import json
import time
import types
import unittest

from backend.core import config
from backend.core.account_pool import Account, AccountPool, LocalBackpressureError


def _future_jwt() -> str:
    header = base64.b64encode(json.dumps({"alg": "none"}).encode()).rstrip(b"=").decode()
    payload = base64.b64encode(json.dumps({"exp": int(time.time()) + 3600}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}."


class DummyDB:
    async def get(self):
        return []

    async def set(self, _value):
        return None


class AccountPoolLimitsTest(unittest.TestCase):
    def test_account_effective_max_inflight_uses_runtime_setting_after_warmup(self):
        old_value = config.settings.MAX_INFLIGHT_PER_ACCOUNT
        try:
            config.settings.MAX_INFLIGHT_PER_ACCOUNT = 4
            acc = Account("user@example.com", token=_future_jwt())
            acc.created_at = time.time() - 3 * 3600
            acc.warmup_until = 0
            self.assertEqual(acc.effective_max_inflight, 4)
        finally:
            config.settings.MAX_INFLIGHT_PER_ACCOUNT = old_value

    def test_pool_availability_and_status_use_configured_capacity(self):
        pool_settings = types.SimpleNamespace(MAX_INFLIGHT_PER_ACCOUNT=4, MAX_WAITING_REQUESTS=100)
        pool = AccountPool(DummyDB(), settings=pool_settings)
        acc = Account("user@example.com", token=_future_jwt())
        acc.created_at = time.time() - 3 * 3600
        acc.warmup_until = 0
        pool._accounts = [acc]

        acc.inflight = 3
        self.assertTrue(pool._is_available(acc))
        acc.inflight = 4
        self.assertFalse(pool._is_available(acc))

        status = pool.status()
        self.assertEqual(status["capacity"], 4)
        self.assertEqual(status["max_inflight_per_account"], 4)
        self.assertEqual(status["queued"], 0)

    def test_acquire_wait_rejects_when_local_queue_is_full(self):
        async def run_case():
            pool_settings = types.SimpleNamespace(MAX_INFLIGHT_PER_ACCOUNT=1, MAX_WAITING_REQUESTS=1)
            pool = AccountPool(DummyDB(), settings=pool_settings)
            pool._waiting_count = 1
            with self.assertRaises(LocalBackpressureError):
                await pool.acquire_wait(timeout=0.01)

        asyncio.run(run_case())

    def test_acquire_wait_with_zero_queue_allows_immediate_account_only(self):
        async def run_case():
            pool_settings = types.SimpleNamespace(MAX_INFLIGHT_PER_ACCOUNT=1, MAX_WAITING_REQUESTS=0)
            pool = AccountPool(DummyDB(), settings=pool_settings)
            acc = Account("user@example.com", token=_future_jwt())
            acc.created_at = time.time() - 3 * 3600
            acc.warmup_until = 0
            pool._accounts = [acc]
            pool._rebuild_heap()

            acquired = await pool.acquire_wait(timeout=0.01)
            self.assertIs(acquired, acc)
            self.assertEqual(pool._waiting_count, 0)

            with self.assertRaises(LocalBackpressureError):
                await pool.acquire_wait(timeout=0.01)

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
