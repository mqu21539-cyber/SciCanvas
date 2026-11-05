# -*- coding: utf-8 -*-
"""把 Coder 模型产出的「50 行 JS」拼进全息底座。

这是路线 C 的关键一步：模型不再写 600 行 HTML，只写物理逻辑。
底座（holo_shell.py，在 B 方案目录里）负责四层舞台、示波器、时间控制、滤镜、残影。

拼装前会做一次结构校验；不合格就抛 HoloError，调用方据此回落到"模型写整份 HTML"的老路。
"""
from __future__ import annotations

import os
import re
import sys

MIN_JS = 120
MAX_JS = 24000

# 出现这些说明模型又去写整份文档了，属于契约违规
_DOC_MARKERS = ("<!doctype", "<html", "<body", "<style", "<head")

_FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$", re.MULTILINE)


class HoloError(ValueError):
    """JS 片段不满足契约。"""


def _holo_shell():
    """惰性导入 B 方案目录里的底座（目录名含中文，必须用路径插入）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    b_dir = os.path.normpath(os.path.join(here, "..", "..", "B-模板化生成"))
    if b_dir not in sys.path:
        sys.path.insert(0, b_dir)
    import holo_shell  # noqa: PLC0415

    return holo_shell


def clean_js(raw: str) -> str:
    """去掉代码围栏、<script> 包裹与首尾噪声。"""
    text = (raw or "").strip()
    text = _FENCE.sub("", text).strip()

    m = re.search(r"<script[^>]*>(.*?)</script>", text, re.DOTALL | re.IGNORECASE)
    if m:
        text = m.group(1).strip()

    low = text.lower()
    if any(tag in low for tag in _DOC_MARKERS):
        raise HoloError("片段里混进了 HTML 文档结构")
    return text


def validate(js: str) -> None:
    if len(js) < MIN_JS:
        raise HoloError(f"JS 太短（{len(js)} 字符），大概率没写完整")
    if len(js) > MAX_JS:
        raise HoloError(f"JS 太长（{len(js)} 字符），不符合 50 行契约")
    if not re.search(r"window\.(frame|reset)\s*=", js):
        raise HoloError("没有定义 window.frame / window.reset")
    if "requestAnimationFrame" in js:
        raise HoloError("底座已在跑循环，片段里不该再写 requestAnimationFrame")
    if re.search(r"<canvas|createElement\(\s*['\"]canvas", js, re.IGNORECASE):
        raise HoloError("底座是 SVG 四层，不该再用 canvas")
    if abs(js.count("{") - js.count("}")) > 2:
        raise HoloError("花括号不平衡")


def _spec(plan: dict, controls: list[dict], metrics: list[dict]) -> dict:
    return {
        "title": plan.get("title") or "科学实验",
        "subtitle": plan.get("subtitle") or "",
        "formula": plan.get("formula_latex") or "",
        "controls": controls,
        "metrics": metrics,
    }


def normalize_controls(raw, limit: int = 4) -> list[dict]:
    """把 Planner 给的参数收敛成底座能吃的格式，缺字段就补默认值。"""
    out = []
    for i, c in enumerate(raw or []):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("id") or f"p{i}").strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,15}", cid):
            cid = f"p{i}"
        try:
            mn = float(c.get("min", 0))
            mx = float(c.get("max", 1))
            df = float(c.get("default", (mn + mx) / 2))
        except (TypeError, ValueError):
            mn, mx, df = 0.0, 1.0, 0.5
        if mx <= mn:
            mx = mn + 1
        df = min(max(df, mn), mx)
        step = c.get("step", (mx - mn) / 100)
        try:
            step = float(step)
        except (TypeError, ValueError):
            step = (mx - mn) / 100
        if step <= 0:
            step = (mx - mn) / 100
        out.append(
            {
                "id": cid,
                "label": str(c.get("label") or cid)[:18],
                "unit": str(c.get("unit") or "")[:8],
                "min": mn,
                "max": mx,
                "step": step,
                "default": df,
            }
        )
        if len(out) >= limit:
            break

    if not out:  # 兜底：至少给一个能拖的
        out.append(
            {"id": "k", "label": "强度", "unit": "", "min": 0.1, "max": 3.0, "step": 0.1, "default": 1.0}
        )
    return out


def normalize_metrics(raw, limit: int = 4) -> list[dict]:
    out = []
    for i, m in enumerate(raw or []):
        if isinstance(m, dict) and m.get("id"):
            mid = re.sub(r"[^A-Za-z0-9_]", "", str(m["id"]))[:16] or f"m{i}"
            out.append({"id": mid, "label": str(m.get("label") or mid)[:16]})
        if len(out) >= limit:
            break
    while len(out) < 4:
        out.append({"id": f"m{len(out)}", "label": f"指标 {len(out) + 1}"})
    return out


def build(plan: dict, js: str) -> str:
    """校验 + 拼装，返回完整单文件 HTML。不合格时抛 HoloError。"""
    cleaned = clean_js(js)
    validate(cleaned)
    shell = _holo_shell()
    spec = _spec(
        plan,
        normalize_controls(plan.get("controls")),
        normalize_metrics(plan.get("metrics")),
    )
    return shell.render(spec, cleaned)