"""
admin/ -- 管理后台 API（拆分为多个子模块）
路由聚合 + 共享鉴权依赖。
"""

from fastapi import APIRouter, HTTPException, Request
from backend.core.config import settings as app_settings

router = APIRouter()


def _require_admin(request: Request):
    """共享的管理员鉴权依赖。"""
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").strip() if auth.startswith("Bearer ") else ""
    if not token:
        token = request.headers.get("x-api-key", "").strip()
    if not token:
        # SSE EventSource 不支持自定义 header，允许 query param
        token = request.query_params.get("key", "").strip()
    if token != app_settings.ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return token


# 挂载子模块路由
from .accounts import router as accounts_router  # noqa: E402
from .keys import router as keys_router  # noqa: E402
from .settings import router as settings_router  # noqa: E402
from .stats import router as stats_router  # noqa: E402
from .cache import router as cache_router  # noqa: E402

router.include_router(accounts_router)
router.include_router(keys_router)
router.include_router(settings_router)
router.include_router(stats_router)
router.include_router(cache_router)
