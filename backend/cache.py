# -*- coding: utf-8 -*-
"""生成结果缓存。

同一个提示词 + 同一策略再点一次，没必要再花 25 秒和 7,000+ tokens。
缓存落在 backend/.cache/（已 gitignore），按 SHA256 前 16 位命名，原子写。

环境变量：
    SCICANVAS_CACHE_DIR   缓存目录（默认 backend/.cache）
    SCICANVAS_CACHE_TTL   过期秒数（默认 7 天）
    SCICANVAS_NO_CACHE=1  完全绕过缓存
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

CACHE_DIR = Path(os.getenv("SCICANVAS_CACHE_DIR", Path(__file__).resolve().parent / ".cache"))
TTL_SECONDS = int(os.getenv("SCICANVAS_CACHE_TTL", str(7 * 24 * 3600)))


def enabled() -> bool:
    return os.getenv("SCICANVAS_NO_CACHE", "").strip() not in ("1", "true", "yes")


def key_for(prompt: str, strategy: str) -> str:
    raw = f"{strategy}\x00{prompt.strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def get(key: str) -> dict | None:
    if not enabled():
        return None
    path = _path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if time.time() - float(data.get("ts", 0)) > TTL_SECONDS:
        try:
            path.unlink()
        except OSError:
            pass
        return None
    payload = data.get("payload")
    return payload if isinstance(payload, dict) else None


def put(key: str, prompt: str, strategy: str, payload: dict) -> bool:
    """写缓存。失败只返回 False，不影响主流程。"""
    if not enabled():
        return False
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        body = {
            "ts": time.time(),
            "prompt": prompt,
            "strategy": strategy,
            "payload": payload,
        }
        tmp = CACHE_DIR / f".{key}.tmp"
        tmp.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_path(key))  # 原子替换：并发写不会读到半个文件
        return True
    except OSError:
        return False


def stats() -> dict:
    """给 /api/cache 用：条数与总字节数。"""
    if not CACHE_DIR.exists():
        return {"entries": 0, "bytes": 0, "dir": str(CACHE_DIR), "ttl_seconds": TTL_SECONDS}
    entries, total = 0, 0
    for p in CACHE_DIR.glob("*.json"):
        entries += 1
        total += p.stat().st_size
    return {"entries": entries, "bytes": total, "dir": str(CACHE_DIR), "ttl_seconds": TTL_SECONDS}


def clear() -> int:
    if not CACHE_DIR.exists():
        return 0
    removed = 0
    for p in CACHE_DIR.glob("*.json"):
        try:
            p.unlink()
            removed += 1
        except OSError:
            pass
    return removed