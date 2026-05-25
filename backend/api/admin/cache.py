"""
cache.py -- 缓存管理端点
"""

from fastapi import APIRouter, Depends
from backend.services.image_proxy import get_cache_stats, list_images, delete_image, clear_all_images
from . import _require_admin

router = APIRouter()


@router.get("/cache")
async def cache_stats(_=Depends(_require_admin)):
    """获取缓存统计"""
    return {"local_image": get_cache_stats()}


@router.get("/cache/list")
async def cache_list(
    page: int = 1,
    page_size: int = 100,
    _=Depends(_require_admin),
):
    """列出缓存文件"""
    return list_images(page, page_size)


@router.post("/cache/clear")
async def cache_clear(_=Depends(_require_admin)):
    """清空所有图片缓存"""
    removed = clear_all_images()
    return {"ok": True, "removed": removed}


@router.post("/cache/delete")
async def cache_delete(name: str = "", _=Depends(_require_admin)):
    """删除单个缓存文件"""
    if not name:
        return {"ok": False, "error": "Missing file name"}
    deleted = delete_image(name)
    return {"ok": deleted, "deleted": name if deleted else None}
