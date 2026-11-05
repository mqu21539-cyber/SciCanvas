import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import router
import cache
from agents import fix_lab_code

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scicanvas")

app = FastAPI(title="SciCanvas API", version="1.1.0")

# 早期版本用的是 allow_origins=["*"] + allow_credentials=True，
# 浏览器会直接拒绝这种组合；这里改为显式来源白名单。
_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str
    # auto：模板优先、Agent 兜底；template：只走模板；agent：只走双 Agent
    strategy: str = Field(default="auto", pattern="^(auto|template|agent)$")


class FixRequest(BaseModel):
    html: str
    error: str


@app.get("/api/health")
def api_health():
    """供前端与 dsh 插件做可用性探测（比探测 /docs 更轻）"""
    return {
        "status": "ok",
        "has_key": bool(os.getenv("DEEPSEEK_API_KEY")),
        "templates": router.template_names(),
        "cache": cache.stats(),
    }


@app.get("/api/templates")
def api_templates():
    """列出 B 方案可用模板（前端可据此做快捷入口）。"""
    return {"templates": router.template_catalog()}


@app.get("/api/cache")
def api_cache_stats():
    """缓存条数与占用，便于观察命中收益。"""
    return cache.stats()


@app.delete("/api/cache")
def api_cache_clear():
    """清空缓存（改过 prompt 或模板后建议清一次）。"""
    return {"removed": cache.clear()}


@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    try:
        return router.route_and_generate(req.prompt, strategy=req.strategy)
    except Exception as e:  # noqa: BLE001 - 统一转成 500 返回给前端展示
        logger.exception("generate failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fix")
def api_fix(req: FixRequest):
    try:
        fixed_html = fix_lab_code(req.html, req.error)
        return {"html": fixed_html}
    except Exception as e:  # noqa: BLE001
        logger.exception("fix failed")
        raise HTTPException(status_code=500, detail=str(e))