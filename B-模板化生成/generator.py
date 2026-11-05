# -*- coding: utf-8 -*-
"""SciCanvas B 方案：模板化生成器。

与 A 方案（让模型直接写 500 行 HTML）相反，这里模型只输出一小段 JSON：
    选哪个模板 + 参数取值 + 标题/副标题/公式/挑战题

HTML 由模板渲染，因此：
  * 输出 token 量从 ~7000 降到 ~400，耗时目标 10–15s；
  * 模板内的物理与视觉恒定正确，模型编不出错误公式；
  * 代价是覆盖面受模板库限制。

用法：
    python generator.py --list
    python generator.py --plan examples/plan-oscillator.json --out out/demo.html
    python generator.py --template projectile --params "v0=40,ang=60,k=0.15"
    python generator.py --text "演示单摆阻尼振动" --out out/from-text.html   # 需 DEEPSEEK_API_KEY
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows 控制台/管道默认是 GBK，公式里的 '−' 这类字符会直接把 --list 打崩。
# 统一成 UTF-8，谁的终端都不该因为一个减号挂掉。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

import templates  # noqa: E402
from templates import get  # noqa: E402

TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------- 外壳
def _shell(head_inner, body_inner, title):
    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n<head>\n'
        "<script>\n"
        "window.onerror = function(msg, url, line, col, error) {\n"
        "  window.parent.postMessage({ type: 'SCICANVAS_ERROR', message: msg, line: line }, '*');\n"
        "};\n"
        "</script>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{title}</title>\n"
        '<script src="https://cdn.tailwindcss.com"></script>\n'
        "<style>\n"
        "  html, body { height: 100%; margin: 0; }\n"
        "  body { font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }\n"
        "  canvas { display: block; }\n"
        "  input[type=range] { -webkit-appearance: none; appearance: none; height: 6px; border-radius: 9999px; background: #1e293b; outline: none; }\n"
        "  input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 15px; height: 15px; border-radius: 50%; background: #38bdf8; box-shadow: 0 0 8px #38bdf8; cursor: pointer; }\n"
        "  input[type=range]::-moz-range-thumb { width: 15px; height: 15px; border: none; border-radius: 50%; background: #38bdf8; box-shadow: 0 0 8px #38bdf8; cursor: pointer; }\n"
        "</style>\n"
        f"{head_inner}"
        "</head>\n"
        '<body class="bg-slate-950 text-slate-100 min-h-screen">\n'
        f"{body_inner}\n"
        "</body>\n</html>\n"
    )


# --------------------------------------------------------------------- 渲染
def normalize_plan(plan: dict) -> dict:
    """补齐缺省字段：模板必须存在，参数必须落在模板声明的范围内。"""
    name = plan.get("template", "oscillator")
    mod = get(name)
    meta = mod.META

    merged = {}
    for c in meta["controls"]:
        merged[c["id"]] = c["default"]
    for k, v in (plan.get("params") or {}).items():
        if k in merged:
            merged[k] = v

    out = {
        "template": name,
        "title": plan.get("title") or meta["title"],
        "subtitle": plan.get("subtitle") or meta.get("category", ""),
        "formula": plan.get("formula") or meta["formula"],
        "challenge": plan.get("challenge") or "拖动滑块，观察参数变化时曲线的响应。",
        "params": merged,
    }
    return out


def render_plan(plan: dict) -> str:
    plan = normalize_plan(plan)
    mod = get(plan["template"])
    copy = {k: plan[k] for k in ("title", "subtitle", "formula", "challenge")}
    body = mod.build(plan["params"], copy)

    # 全息底座（holo_shell）返回的就是一份完整 HTML；旧模板只返回 body 片段。
    # 两种模板共存期间按内容判断，别把完整文档再套一层壳——那样浏览器会解析中断，
    # 表现为整页空白（踩过）。
    if body.lstrip().startswith("<!DOCTYPE html>"):
        return body

    payload = json.dumps(
        {"params": plan["params"], "controls": mod.META["controls"]}, ensure_ascii=False
    )
    inner = f"<script>window.__SCICANVAS__ = {payload};</script>\n" + body
    return _shell("", inner, plan["title"])


# --------------------------------------------------------------------- 选模板
PLANNER_PROMPT = """你是科学可视化编排器。你不写代码，只从给定模板中挑选一个，并给出参数与文案。

可用模板（name / 适用概念 / 参数范围）：
{templates}

严格输出 JSON，不要解释，不要 Markdown 围栏：
{{
  "template": "模板 name",
  "title": "实验标题（中文，简短）",
  "subtitle": "一句话解释核心机制",
  "formula": "核心公式（纯文本）",
  "challenge": "一句反直觉的思考题，诱导用户拖动滑块验证",
  "params": {{ "参数id": 数值 }}
}}

规则：
1. 只能从上面列出的模板中选，参数值必须落在给定区间内；
2. 如果概念明显不属于任何模板，仍然选最接近的一个，并在 subtitle 里说明是近似；
3. params 只填需要偏离默认值的项，未提到的用默认值。
"""


def _templates_brief() -> str:
    lines = []
    for meta in templates.list_templates():
        ctrl = "; ".join(
            f'{c["id"]}({c["label"]}) {c["min"]}~{c["max"]} 默认{c["default"]}'
            for c in meta["controls"]
        )
        lines.append(f'- {meta["name"]}：{meta["category"]}｜{meta["formula"]}｜参数：{ctrl}')
    return "\n".join(lines)


def plan_from_text(text: str) -> dict:
    """调用 DeepSeek 只产 JSON（约 300–500 tokens），不做代码生成。"""
    try:
        from dotenv import load_dotenv
        from openai import OpenAI
    except ImportError:
        raise SystemExit("需要 openai 与 python-dotenv：pip install openai python-dotenv")

    load_dotenv(os.path.join(TEMPLATE_DIR, ".env"))
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("缺少 DEEPSEEK_API_KEY（可写在 B-模板化生成/.env 里）")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        timeout=60.0,
    )
    resp = client.chat.completions.create(
        model="deepseek-chat",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PLANNER_PROMPT.format(templates=_templates_brief())},
            {"role": "user", "content": text},
        ],
    )
    raw = resp.choices[0].message.content
    plan = json.loads(raw)
    usage = getattr(resp, "usage", None)
    if usage:
        print(f"[plan] tokens in/out = {usage.prompt_tokens}/{usage.completion_tokens}")
    return plan


# --------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="SciCanvas B 方案：模板化生成器")
    ap.add_argument("--list", action="store_true", help="列出可用模板")
    ap.add_argument("--plan", help="从 JSON 文件读取 plan")
    ap.add_argument("--text", help="自然语言概念，调用模型选模板（需 API Key）")
    ap.add_argument("--template", help="直接指定模板名")
    ap.add_argument("--params", help='参数覆盖，如 "v0=40,ang=60,k=0.15"')
    ap.add_argument("--out", help="输出 HTML 路径")
    args = ap.parse_args(argv)

    if args.list:
        for meta in templates.list_templates():
            print(f'\n[{meta["name"]}] {meta["title"]}  ({meta["category"]})')
            print(f'  公式: {meta["formula"]}')
            for c in meta["controls"]:
                print(f'  参数: {c["id"]:<6} {c["label"]}  {c["min"]}~{c["max"]}  默认 {c["default"]}')
        return 0

    plan = None
    if args.plan:
        with open(args.plan, encoding="utf-8") as f:
            plan = json.load(f)
    elif args.text:
        plan = plan_from_text(args.text)
        print("[plan]", json.dumps(plan, ensure_ascii=False))
    elif args.template:
        plan = {"template": args.template, "params": {}}

    if plan is None:
        ap.print_help()
        return 2

    if args.params:
        parsed = {}
        for pair in args.params.split(","):
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            parsed[k.strip()] = float(v)
        plan.setdefault("params", {}).update(parsed)

    html = render_plan(plan)
    out = args.out or os.path.join("out", f'{plan.get("template", "lab")}.html')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    print(f"[ok] {len(html)} 字符 -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())