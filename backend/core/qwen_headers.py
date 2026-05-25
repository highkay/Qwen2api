"""
qwen_headers.py -- Qwen 网页请求头统一构造
"""

from backend.core.config import settings


BASE_URL = "https://chat.qwen.ai"


def qwen_impersonate() -> str:
    chrome_version = str(getattr(settings, "QWEN_CHROME_VERSION", "124")).strip() or "124"
    return str(getattr(settings, "QWEN_IMPERSONATE", "") or f"chrome{chrome_version}")


def qwen_user_agent() -> str:
    chrome_version = str(getattr(settings, "QWEN_CHROME_VERSION", "124")).strip() or "124"
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36"
    )


def qwen_api_headers(
    token: str | None = None,
    *,
    content_type: str | None = None,
    accept: str = "application/json, text/plain, */*",
    stream: bool = False,
    extra: dict | None = None,
) -> dict:
    chrome_version = str(getattr(settings, "QWEN_CHROME_VERSION", "124")).strip() or "124"
    sec_ch_version = chrome_version.split(".", 1)[0]
    headers = {
        "accept": "text/event-stream" if stream else accept,
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "cache-control": "no-cache",
        "origin": BASE_URL,
        "pragma": "no-cache",
        "referer": f"{BASE_URL}/",
        "sec-ch-ua": f'"Chromium";v="{sec_ch_version}", "Google Chrome";v="{sec_ch_version}", "Not=A?Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": qwen_user_agent(),
        "version": str(getattr(settings, "QWEN_WEB_VERSION", "0.2.46")),
    }
    bx_v = str(getattr(settings, "QWEN_BX_V", "")).strip()
    if bx_v:
        headers["bx-v"] = bx_v
    if token:
        headers["authorization"] = f"Bearer {token}"
    if content_type:
        headers["content-type"] = content_type
    if stream:
        headers["accept-encoding"] = "identity"
        headers["x-accel-buffering"] = "no"
    if extra:
        headers.update(extra)
    return headers
