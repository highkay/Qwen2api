"""
image_proxy.py -- 图片代理服务（磁盘持久化版）
仿 grok2api 的 media_cache 机制：图片存到 data/files/images/，支持容量管理。
"""

import hashlib
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Optional

from backend.core.config import settings, DATA_DIR

log = logging.getLogger("qwen2api.image_proxy")

# 图片存储目录
IMAGES_DIR = DATA_DIR / "files" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

_IMAGE_EXTS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"})


def generate_image_id() -> str:
    """生成唯一图片 ID"""
    return uuid.uuid4().hex[:24]


def save_image(data: bytes, content_type: str) -> str:
    """保存图片到磁盘，返回 file_id"""
    file_id = generate_image_id()
    ext = ".png" if "png" in content_type.lower() else ".jpg"
    path = IMAGES_DIR / f"{file_id}{ext}"
    path.write_bytes(data)
    log.info(f"[ImageProxy] 已保存: {file_id}{ext} ({len(data)} bytes)")
    # 容量管理
    _enforce_limit()
    return file_id


def get_image_path(file_id: str) -> Optional[Path]:
    """根据 file_id 查找图片文件路径"""
    if not re.fullmatch(r"[0-9a-f]{16,36}", file_id):
        return None
    for ext in (".jpg", ".png", ".jpeg", ".gif", ".webp"):
        path = IMAGES_DIR / f"{file_id}{ext}"
        if path.exists():
            return path
    return None


def get_image_mime(path: Path) -> str:
    """根据扩展名返回 MIME 类型"""
    ext = path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}
    return mime_map.get(ext, "image/jpeg")


def list_images(page: int = 1, page_size: int = 100) -> dict:
    """列出缓存的图片文件"""
    files = sorted(
        (f for f in IMAGES_DIR.glob("*") if f.is_file() and f.suffix.lower() in _IMAGE_EXTS),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    total = len(files)
    start = (page - 1) * page_size
    chunk = files[start:start + page_size]
    items = []
    for f in chunk:
        st = f.stat()
        items.append({
            "name": f.name,
            "size_bytes": st.st_size,
            "modified_at": st.st_mtime,
        })
    return {"total": total, "page": page, "page_size": page_size, "items": items}


def get_cache_stats() -> dict:
    """获取图片缓存统计"""
    files = [f for f in IMAGES_DIR.glob("*") if f.is_file() and f.suffix.lower() in _IMAGE_EXTS]
    total_size = sum(f.stat().st_size for f in files)
    limit_mb = getattr(settings, "IMAGE_CACHE_MAX_MB", 100)
    limit_bytes = limit_mb * 1024 * 1024
    usage_ratio = (total_size / limit_bytes) if limit_bytes > 0 else 0
    return {
        "count": len(files),
        "size_mb": round(total_size / 1024 / 1024, 2),
        "size_bytes": total_size,
        "limit_mb": limit_mb,
        "limit_bytes": limit_bytes,
        "usage_ratio": round(usage_ratio, 4),
        "usage_percent": round(usage_ratio * 100, 1),
    }


def delete_image(name: str) -> bool:
    """删除单个图片"""
    path = IMAGES_DIR / name
    if path.exists() and path.is_file():
        path.unlink()
        return True
    return False


def clear_all_images() -> int:
    """清空所有图片缓存"""
    removed = 0
    for f in IMAGES_DIR.glob("*"):
        if f.is_file() and f.suffix.lower() in _IMAGE_EXTS:
            f.unlink()
            removed += 1
    return removed


def _enforce_limit():
    """容量管理：超限后按最旧文件优先清理到 60%"""
    limit_mb = getattr(settings, "IMAGE_CACHE_MAX_MB", 100)
    if limit_mb <= 0:
        return
    limit_bytes = limit_mb * 1024 * 1024
    files = sorted(
        (f for f in IMAGES_DIR.glob("*") if f.is_file() and f.suffix.lower() in _IMAGE_EXTS),
        key=lambda f: f.stat().st_mtime,
    )
    total_size = sum(f.stat().st_size for f in files)
    if total_size <= limit_bytes:
        return
    target = int(limit_bytes * 0.6)
    removed = 0
    for f in files:
        if total_size <= target:
            break
        size = f.stat().st_size
        f.unlink()
        total_size -= size
        removed += 1
    if removed:
        log.info(f"[ImageProxy] 容量清理: 删除 {removed} 个文件，当前 {total_size // 1024 // 1024}MB")


async def download_and_save(url: str) -> Optional[str]:
    """下载图片并保存到磁盘，返回 file_id"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                log.warning(f"[ImageProxy] 下载失败: {url} -> {resp.status_code}")
                return None
            content_type = resp.headers.get("content-type", "image/png")
            return save_image(resp.content, content_type)
    except Exception as e:
        log.warning(f"[ImageProxy] 下载异常: {url} -> {e}")
        return None


async def proxy_image_urls(text: str, app_url: str) -> str:
    """将文本中的上游图片 URL 替换为本地代理 URL"""
    if not app_url:
        return text
    app_url = app_url.rstrip("/")
    pattern = re.compile(r'!\[([^\]]*)\]\((https?://[^\s\)]+)\)')
    matches = list(pattern.finditer(text))
    if not matches:
        return text
    result = text
    for m in reversed(matches):
        alt = m.group(1)
        url = m.group(2)
        file_id = await download_and_save(url)
        if file_id:
            new_str = f"![{alt}]({app_url}/v1/files/image?id={file_id})"
            result = result[:m.start()] + new_str + result[m.end():]
    return result


# 兼容旧接口
def get_cached_image(image_id: str) -> Optional[dict]:
    """兼容旧的内存缓存接口"""
    path = get_image_path(image_id)
    if not path:
        return None
    return {"data": path.read_bytes(), "content_type": get_image_mime(path)}
