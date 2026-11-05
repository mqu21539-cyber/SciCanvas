import asyncio
import json
import logging
import os
import threading
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import cache
import router
from agents import fix_lab_code, fix_lab_snippet

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
    # 报错行号（来自沙盒的 window.onerror 回传）。给了就走"只修这一段"的快路径
    line: int | None = None
    window: int = 60


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


@app.post("/api/generate/stream")
async def api_generate_stream(req: GenerateRequest):
    """SSE 版生成：把「分诊 → Planner → Coder」的真实阶段推给前端。

    生成是同步阻塞的，所以放工作线程；但**消费端必须是原生异步生成器**——
    早先用同步生成器时，Starlette 会把它丢进线程池迭代，首帧会被憋到下一个事件才刷出去
    （实测服务端 0.000s 产生、客户端 1.7s 才收到）。
    """
    loop = asyncio.get_running_loop()
    events: asyncio.Queue = asyncio.Queue()
    stop_beat = threading.Event()
    t_start = time.time()

    def emit(payload: dict):
        item = {"t": round(time.time() - t_start, 3), **payload}
        loop.call_soon_threadsafe(events.put_nowait, item)

    def heartbeat():
        """Coder 一次调用要 20 秒左右，中间没有任何事件——每 3 秒补一个心跳。"""
        waited = 0
        while not stop_beat.wait(3):
            waited += 3
            emit({"stage": "tick", "elapsed": waited})

    def worker():
        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()
        try:
            out = router.route_and_generate(req.prompt, strategy=req.strategy, emit=emit)
            emit({"stage": "done", **out})
        except Exception as e:  # noqa: BLE001
            logger.exception("stream generate failed")
            emit({"stage": "error", "detail": str(e)})
        finally:
            stop_beat.set()
            loop.call_soon_threadsafe(events.put_nowait, None)

    threading.Thread(target=worker, daemon=True).start()

    async def event_source():
        # 首帧补到 ~2KB：小包在某些链路上会被攒着不发（实测本机环回也会）。
        # SSE 注释行浏览器会忽略，只占一次写入。
        yield ": " + (" " * 2040) + "\n\n"
        while True:
            item = await events.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 反向代理别缓冲
        },
    )


@app.post("/api/fix")
def api_fix(req: FixRequest):
    """默认整份回传修复。

    片段模式（只回传出错附近）实测能省约 2/3 输入 token，但三种拼接实现都会在
    「删掉一行声明」这类真实故障上产出坏文件（语法错或画面全空），而服务端没有
    JS 运行时可以验证修好没修好。所以默认关闭，留 SCICANVAS_SNIPPET_FIX=1 作实验开关。
    """
    usage: dict = {}
    try:
        if req.line and os.getenv("SCICANVAS_SNIPPET_FIX", "").strip() in ("1", "true", "yes"):
            try:
                fixed_html = fix_lab_snippet(req.html, req.error, req.line, req.window, usage)
                logger.info("fix via snippet: %s", usage)
                return {"html": fixed_html, "mode": "snippet", "usage": usage}
            except Exception as e:  # noqa: BLE001
                logger.info("snippet 修复未成功，回落整份：%s", e)

        fixed_html = fix_lab_code(req.html, req.error, usage)
        return {"html": fixed_html, "mode": usage.get("mode", "full"), "usage": usage}
    except Exception as e:  # noqa: BLE001
        logger.exception("fix failed")
        raise HTTPException(status_code=500, detail=str(e))