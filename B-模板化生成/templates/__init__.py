# -*- coding: utf-8 -*-
"""B 方案模板库。

每个模板模块暴露：
    META = {name, title, category, formula, controls[], metrics[]}
    build(params, copy) -> str    # 返回 body 内部片段（含 canvas、控件、<script>）

模板只接受"参数"，不接受"代码"。物理与视觉由模板作者负责，模型只负责选模板 + 填参数。

注意：辅助函数必须在导入子模块之前定义——子模块会反向 import 它们。
"""


def controls_html(meta, params):
    rows = []
    for c in meta["controls"]:
        val = params.get(c["id"], c["default"])
        unit = f' <span class="text-slate-500">({c["unit"]})</span>' if c.get("unit") else ""
        rows.append(
            f'<div>\n'
            f'  <div class="flex justify-between text-xs mb-1">\n'
            f'    <label class="text-slate-300">{c["label"]}{unit}</label>\n'
            f'    <span id="val_{c["id"]}" class="font-mono text-cyan-400">{val}</span>\n'
            f'  </div>\n'
            f'  <input id="{c["id"]}" type="range" min="{c["min"]}" max="{c["max"]}" '
            f'step="{c["step"]}" value="{val}" class="w-full accent-cyan-400">\n'
            f'</div>'
        )
    return "\n".join(rows)


def metrics_html(meta):
    cells = []
    for m in meta["metrics"]:
        cells.append(
            f'<div class="bg-slate-950/60 rounded-lg p-2.5 border border-slate-800">\n'
            f'  <div class="text-[10px] text-slate-500 uppercase tracking-wide">{m["label"]}</div>\n'
            f'  <div id="m_{m["id"]}" class="text-base font-bold {m.get("color", "text-cyan-400")} font-mono">'
            f'{m.get("initial", "--")}</div>\n'
            f'</div>'
        )
    return "\n".join(cells)


# --- 子模块必须在这里导入：它们会 from . import controls_html ---
from . import oscillator, projectile  # noqa: E402  isort:skip

MODULES = {mod.META["name"]: mod for mod in (oscillator, projectile)}


def get(name):
    if name not in MODULES:
        raise KeyError(f"未知模板 {name!r}，可用：{', '.join(MODULES)}")
    return MODULES[name]


def list_templates():
    return [m.META for m in MODULES.values()]