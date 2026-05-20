import unittest
from unittest.mock import patch

from backend.services.mail_service import TempMailClient, VipMailClient


class FakeResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data
        self.text = text
        self.headers = {}

    def json(self):
        if self._data is None:
            raise ValueError("not json")
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class TempMailClientTest(unittest.TestCase):
    def test_private_site_password_falls_back_to_admin_key_and_inbox_uses_offset(self):
        calls = []

        class FakeClient:
            def __init__(self, timeout=0, **_kwargs):
                self.timeout = timeout

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def post(self, url, json=None, headers=None):
                calls.append(("post", url, json, headers))
                return FakeResponse(
                    data={
                        "address": "qa@example.test",
                        "jwt": "jwt-token",
                        "address_id": 1,
                    }
                )

            def get(self, url, params=None, headers=None):
                calls.append(("get", url, params, headers))
                return FakeResponse(data={"results": [], "count": 0})

        with patch("backend.services.mail_service.httpx.Client", FakeClient):
            client = TempMailClient("https://mail.example", "admin-secret")
            created = client.create_address_sync(name="qa")
            link = client.poll_for_activation_link(created["jwt"], max_polls=1, interval=0)

        self.assertIsNone(link)
        post_call = calls[0]
        self.assertEqual(post_call[3]["x-admin-auth"], "admin-secret")
        self.assertEqual(post_call[3]["x-custom-auth"], "admin-secret")
        get_call = calls[1]
        self.assertEqual(get_call[2], {"limit": 5, "offset": 0})
        self.assertEqual(get_call[3]["Authorization"], "Bearer jwt-token")
        self.assertEqual(get_call[3]["x-custom-auth"], "admin-secret")

    def test_private_site_password_can_be_separate_from_admin_key(self):
        calls = []

        class FakeClient:
            def __init__(self, timeout=0, **_kwargs):
                self.timeout = timeout

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def post(self, url, json=None, headers=None):
                calls.append(headers)
                return FakeResponse(data={"address": "qa@example.test", "jwt": "jwt-token"})

        with patch("backend.services.mail_service.httpx.Client", FakeClient):
            TempMailClient("https://mail.example", "admin-secret", site_password="site-secret").create_address_sync()

        self.assertEqual(calls[0]["x-admin-auth"], "admin-secret")
        self.assertEqual(calls[0]["x-custom-auth"], "site-secret")


class VipMailClientTest(unittest.TestCase):
    def test_create_address_surfaces_provider_error_code(self):
        class FakeClient:
            def __init__(self, timeout=0, **_kwargs):
                self.timeout = timeout

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def post(self, url, json=None, headers=None):
                return FakeResponse(
                    status_code=403,
                    data={
                        "success": False,
                        "error": "API key lacks write permission for this operation",
                        "errorCode": "api_key_write_permission_required",
                    },
                )

        with patch("backend.services.mail_service.httpx.Client", FakeClient):
            with self.assertRaises(Exception) as ctx:
                VipMailClient("AC-test").create_address_sync()

        self.assertIn("api_key_write_permission_required", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
