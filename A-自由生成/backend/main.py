import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import fix_lab_code, generate_lab

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scicanvas")

app = FastAPI(title="SciCanvas API", version="1.0.0")

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


class FixRequest(BaseModel):
    html: str
    error: str


@app.get("/api/health")
def api_health():
    """供前端与 dsh 插件做可用性探测（比探测 /docs 更轻）"""
    return {"status": "ok", "has_key": bool(os.getenv("DEEPSEEK_API_KEY"))}


@app.post("/api/generate")
def api_generate(req: GenerateRequest):
    try:
        return generate_lab(req.prompt)
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
