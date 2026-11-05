# -*- coding: utf-8 -*-
"""混合路由：模板快路径（B）优先，双 Agent 慢路径（A）兜底。

设计目标（对应 docs 里的 v0.2 架构）：
    常见概念 ──► 问模型「属于哪个模板？」──命中──► B 渲染（约 4s，物理必然正确）
                      └──────────未命中──────────► A 双 Agent（约 27s，任意概念）

模板库来自 ../B-模板化生成，路径可用 SCICANVAS_TEMPLATE_DIR 覆盖。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# backend/ -> A-自由生成/ -> 仓库根 -> B-模板化生成
_DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "B-模板化生成"
TEMPLATE_DIR = Path(os.getenv("SCICANVAS_TEMPLATE_DIR", _DEFAULT_TEMPLATE_DIR))

_bgen = None
_load_error = None


def template_lib():
    """惰性加载 B 方案的生成器；目录不存在或依赖缺失时返回 None（路由自动降级）。"""
    global _bgen, _load_error
    if _bgen is not None or _load_error is not None:
        return _bgen
    try:
        if not (TEMPLATE_DIR / "generator.py").exists():
            raise FileNotFoundError(f"未找到模板生成器：{TEMPLATE_DIR / 'generator.py'}")
        if str(TEMPLATE_DIR) not in sys.path:
            sys.path.insert(0, str(TEMPLATE_DIR))
        import generator as bgen  # type: ignore

        _bgen = bgen
    except Exception as e:  # noqa: BLE001
        _load_error = str(e)
        _bgen = None
    return _bgen


def template_names() -> list[str]:
    bgen = template_lib()
    if not bgen:
        return []
    return [m["name"] for m in bgen.templates.list_templates()]


def template_catalog() -> list[dict]:
    bgen = template_lib()
    if not bgen:
        return []
    return bgen.templates.list_templates()


_ROUTER_PROMPT = """你是科学可视化分诊器。判断用户输入的概念能否用下列预置模板**准确**表达。

预置模板：
{catalog}

输出 JSON（不要解释，不要 Markdown 围栏）：
{{
  "match": true 或 false,
  "template": "模板 name（match 为 true 时必填）",
  "confidence": 0.0 到 1.0 的小数,
  "reason": "一句话说明为什么匹配 / 为什么不匹配",
  "title": "实验标题（中文，简短有力）",
  "subtitle": "一句话解释核心机制",
  "formula": "核心公式（纯文本）",
  "challenge": "一句反直觉的思考题，诱导用户拖动滑块验证",
  "params": {{ "参数 id": 数值 }}
}}

判定标准（从严）：
1. 只有当概念的核心机制与模板的物理模型**是同一个**时才 match=true；
2. 只是"看起来相关"（例如问量子隧穿却套用经典波动模板）一律 match=false；
3. match=false 时其余字段可以省略；
4. params 只写需要偏离默认值的项，且必须落在模板给定区间内。
"""


def pick_template(prompt: str, client) -> dict | None:
    """问模型：这个概念能用哪个模板表达？失败或未命中返回 None。"""
    catalog = template_catalog()
    if not catalog:
        return None

    lines = []
    for meta in catalog:
        ctrl = "; ".join(
            f'{c["id"]}({c["label"]}) {c["min"]}~{c["max"]} 默认{c["default"]}' for c in meta["controls"]
        )
        lines.append(f'- {meta["name"]}：{meta["category"]}｜{meta["formula"]}｜参数：{ctrl}')

    resp = client.chat.completions.create(
        model="deepseek-chat",
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _ROUTER_PROMPT.format(catalog="\n".join(lines))},
            {"role": "user", "content": prompt},
        ],
    )
    pick = json.loads(resp.choices[0].message.content)
    if not pick.get("match"):
        return {"match": False, "reason": pick.get("reason", ""), "usage": resp.usage}
    if pick.get("template") not in template_names():
        return {"match": False, "reason": f'模型给出未知模板 {pick.get("template")!r}', "usage": resp.usage}
    return {**pick, "usage": resp.usage}


def route_and_generate(prompt: str, strategy: str = "auto") -> dict:
    """strategy: auto（默认，B 优先 A 兜底）/ template（只用模板）/ agent（只用双 Agent）。"""
    started = time.time()
    meta: dict = {"strategy": strategy, "route_reason": "", "router_ms": None, "template": None}

    if strategy in ("auto", "template"):
        bgen = template_lib()
        if not bgen:
            meta["route_reason"] = f"模板库不可用：{_load_error}"
        else:
            from agents import get_client  # 复用同一个 Key / base_url

            t0 = time.time()
            try:
                pick = pick_template(prompt, get_client())
            except Exception as e:  # noqa: BLE001 - 路由失败不应阻断生成
                pick = None
                meta["route_reason"] = f"分诊失败：{e}"
            meta["router_ms"] = int((time.time() - t0) * 1000)

            if pick and pick.get("match"):
                plan = {
                    "template": pick["template"],
                    "title": pick.get("title") or "",
                    "subtitle": pick.get("subtitle") or "",
                    "formula": pick.get("formula") or "",
                    "challenge": pick.get("challenge") or "",
                    "params": pick.get("params") or {},
                }
                html = bgen.render_plan(plan)
                meta.update(
                    template=pick["template"],
                    route_reason=pick.get("reason", ""),
                    confidence=pick.get("confidence"),
                )
                normalized = {
                    "title": plan["title"] or "模板实验",
                    "subtitle": plan["subtitle"],
                    "formula_latex": plan["formula"],
                    "intuition_challenge": plan["challenge"],
                }
                return {
                    "mode": "template",
                    "plan": normalized,
                    "html": html,
                    "elapsed_ms": int((time.time() - started) * 1000),
                    **meta,
                }
            elif pick:
                meta["route_reason"] = pick.get("reason", "")

    if strategy == "template":
        raise RuntimeError(f"没有匹配的模板：{meta['route_reason'] or '未命中'}")

    from agents import generate_lab

    out = generate_lab(prompt)
    return {
        "mode": "agent",
        "plan": out["plan"],
        "html": out["html"],
        "elapsed_ms": int((time.time() - started) * 1000),
        **meta,
    }