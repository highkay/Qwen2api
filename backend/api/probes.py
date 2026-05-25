"""
probes.py -- 健康检查与模型列表
"""

from fastapi import APIRouter, Request
from backend.core.config import VERSION
from backend.services.model_catalog import fallback_openai_model_entries, model_catalog

router = APIRouter()


@router.get("/health")
@router.get("/healthz")
async def health():
    return {"status": "ok", "version": VERSION}


@router.get("/v1/models")
@router.get("/models")
async def list_models(request: Request):
    """返回兼容 OpenAI /v1/models 格式的模型列表。优先使用 Qwen 动态目录。"""
    qwen_client = getattr(request.app.state, "qwen_client", None)
    if qwen_client is not None:
        data = await model_catalog.get_openai_models(qwen_client)
    else:
        data = fallback_openai_model_entries()
    return {"object": "list", "data": data}
