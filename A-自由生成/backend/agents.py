import difflib
import json
import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

import holo_build
from prompts import (
    CODER_SYSTEM_PROMPT,
    FIXER_SYSTEM_PROMPT,
    HOLO_CODER_PROMPT,
    HOLO_FIXER_PROMPT,
    HOLO_PLANNER_PROMPT,
    PLANNER_SYSTEM_PROMPT,
)

logger = logging.getLogger("scicanvas")

load_dotenv()

# 惰性创建客户端：没有密钥时不应该让整个服务在 import 阶段直接崩掉，
# 而应该只在真正调用生成接口时返回一条人看得懂的错误。
_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "缺少 DEEPSEEK_API_KEY：请把 backend/.env.example 复制为 backend/.env 并填入真实密钥。"
            )
        _client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            timeout=180.0,
        )
    return _client

_FENCE_RE = re.compile(r"```(?:html)?\s*(<!DOCTYPE html>.*?</html>)\s*```", re.DOTALL | re.IGNORECASE)
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def clean_html_output(raw_text: str) -> str:
    """清理模型可能带上的 ```html 标记"""
    match = _FENCE_RE.search(raw_text)
    if match:
        return match.group(1).strip()
    return raw_text.strip()


def clean_json_output(raw_text: str) -> dict:
    """清理模型可能带上的 ```json 标记，并解析为 dict"""
    text = _JSON_FENCE_RE.sub("", raw_text.strip())
    return json.loads(text)


def generate_lab(user_concept: str, on_stage=None) -> dict:
    """Planner -> Coder 双 Agent 流水线（全息 2.5D 契约）。

    Coder 现在只写约 50 行 JS（reset/frame），由 holo_build 拼进四层 SVG 底座。
    片段不合契约（模型跑去写整份 HTML、括号不平衡等）时，自动回落到老的
    「模型写整份 HTML」路径——宁可慢，不能出不来东西。

    on_stage: 可选回调 on_stage("planner"/"coder"/"fallback")，供 SSE 推进度。
    """

    def stage(name):
        if on_stage:
            try:
                on_stage(name)
            except Exception:  # noqa: BLE001 - 进度推送失败不该影响生成
                pass

    # 1. Planner Agent 生成结构化实验蓝图（含参数胶囊与四层分工）
    stage("planner")
    plan_res = get_client().chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": HOLO_PLANNER_PROMPT},
            {"role": "user", "content": f"请为以下科学概念或论文段落设计2D互动实验：\n{user_concept}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    plan_json_str = plan_res.choices[0].message.content
    plan_data = clean_json_output(plan_json_str)

    # 2. Coder Agent 只写物理逻辑
    stage("coder")
    code_res = get_client().chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": HOLO_CODER_PROMPT},
            {"role": "user", "content": f"实验蓝图（JSON）：\n{plan_json_str}\n\n请输出 reset/frame 片段。"},
        ],
        temperature=0.2,
    )
    js_snippet = code_res.choices[0].message.content or ""
    coder_mode = "holo"
    try:
        html_code = holo_build.build(plan_data, js_snippet)
    except holo_build.HoloError as e:
        logger.warning("全息片段不合格（%s），回落整份 HTML 生成", e)
        stage("fallback")
        coder_mode = "full"
        legacy = get_client().chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": CODER_SYSTEM_PROMPT},
                {"role": "user", "content": f"请严格按照以下 JSON 实验蓝图编写单文件 HTML 交互仿真代码：\n{plan_json_str}"},
            ],
            temperature=0.2,
        )
        html_code = clean_html_output(legacy.choices[0].message.content)

    return {"plan": plan_data, "html": html_code, "coder_mode": coder_mode}

    return {"plan": plan_data, "html": html_code}


_HOLO_MARK = "HOLO.L1"
_SCRIPTS = re.compile(r"<script\b[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)


def _fix_holo_snippet(broken_html: str, error_msg: str, usage_out: dict | None) -> str:
    """全息产物只修最后一段 JS，不重写整份 HTML。

    注意：千万别用「从第一个 <script> 到 </script></body>」这种正则——
    它会把底座脚本和模板脚本一起吞掉，结果是把整个四层舞台替换成几十行 JS
    （实测产物从 30KB 掉到 5.6KB，页面直接废掉）。只认最后一个脚本块。
    """
    blocks = list(_SCRIPTS.finditer(broken_html))
    if not blocks:
        raise ValueError("找不到脚本块")
    target = blocks[-1]                     # 最后一个 <script> 就是模型写的那段
    if "HOLO" not in target.group(1):
        raise ValueError("最后一个脚本块不像实验逻辑")

    resp = get_client().chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": HOLO_FIXER_PROMPT},
            {"role": "user", "content": f"报错：{error_msg}\n\n当前 JS：\n{target.group(1)}"},
        ],
        temperature=0.1,
    )
    if usage_out is not None and getattr(resp, "usage", None):
        usage_out["prompt_tokens"] = resp.usage.prompt_tokens
        usage_out["completion_tokens"] = resp.usage.completion_tokens

    if usage_out is not None:
        usage_out["mode"] = "holo-snippet"
    fixed_js = holo_build.clean_js(resp.choices[0].message.content or "")
    if not fixed_js or fixed_js == target.group(1).strip():
        raise ValueError("模型没有给出改动")
    if abs(fixed_js.count("{") - fixed_js.count("}")) > 2:
        raise ValueError("修复后的括号不平衡")
    if not re.search(r"window\.(frame|reset)\s*=", fixed_js):
        raise ValueError("修复后缺少 window.frame/reset")

    merged = broken_html[: target.start(1)] + "\n" + fixed_js + "\n" + broken_html[target.end(1) :]
    # 底座必须还在，否则说明拼错了
    if "id=\"l1\"" not in merged or merged.count("<script") != broken_html.count("<script"):
        raise ValueError("拼接后底座丢失，改走整份修复")
    return merged


def fix_lab_code(broken_html: str, error_msg: str, usage_out: dict | None = None) -> str:
    """修复损坏的实验。

    全息产物（v0.11 起）只重写里面那段 JS；老产物整份回传修复。
    片段修复失败时自动回落整份，别把用户卡在报错页。
    """
    if _HOLO_MARK in broken_html:
        try:
            return _fix_holo_snippet(broken_html, error_msg, usage_out)
        except Exception as e:  # noqa: BLE001
            # 全息产物修不动时，宁可原样返回，也不要整份重写——
            # 整份重写会把四层底座换成模型自己画的 canvas 版，越修越糟。
            logger.info("全息片段修复未成功，原样返回：%s", e)
            if usage_out is not None:
                usage_out["mode"] = "holo-unchanged"
            return broken_html

    fix_res = get_client().chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": FIXER_SYSTEM_PROMPT},
            {"role": "user", "content": f"运行报错信息：{error_msg}\n\n原HTML代码：\n{broken_html}"},
        ],
        temperature=0.1,
    )
    if usage_out is not None and getattr(fix_res, "usage", None):
        usage_out["prompt_tokens"] = fix_res.usage.prompt_tokens
        usage_out["completion_tokens"] = fix_res.usage.completion_tokens
    return clean_html_output(fix_res.choices[0].message.content)


SNIPPET_SYSTEM_PROMPT = """你是前端调试专家。用户会给你一个单文件 HTML 实验中的一小段代码（带绝对行号）和它运行时的报错。

只输出一个 JSON 补丁，不要任何解释：
{"start_line": 起始行号, "end_line": 结束行号, "replacement": "替换后的代码"}

规则：
- 行号必须是用户给你的绝对行号，且落在给出的范围内；
- 只覆盖真正需要改的那几行，最多 25 行；
- replacement 保留该范围内的缩进；
- 如果这段代码看不出问题，输出 {"start_line": 0, "end_line": 0, "replacement": ""}。
"""


def _slice_lines(html: str, line: int, window: int) -> tuple[list[str], int, int]:
    lines = html.splitlines()
    total = len(lines)
    idx = max(0, min(total - 1, line - 1))
    start = max(0, idx - window)
    end = min(total, idx + window + 1)
    return lines, start, end


def fix_lab_snippet(
    html: str, error_msg: str, line: int, window: int = 60, usage_out: dict | None = None
) -> str:
    """只把报错行附近的代码发给模型，让它返回一个行号补丁，再拼回整份文件。

    为什么不"让它重写整段"：实测模型会把片段精简后返回，整段替换会静默删代码
    （拼出过一份不报错但画面全空的 HTML）。改成补丁后只动它明确指定的几行，
    并且每一条都要过行号范围、行数与括号平衡三道检查，任何一道不过就回落整份修复。
    """
    lines, start, end = _slice_lines(html, line, window)
    numbered = "\n".join(f"{start + i + 1}: {l}" for i, l in enumerate(lines[start:end]))

    resp = get_client().chat.completions.create(
        model="deepseek-chat",
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SNIPPET_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"整份文件共 {len(lines)} 行，报错在第 {line} 行。\n"
                    f"下面只给了第 {start + 1}-{end} 行：\n{numbered}\n\n"
                    f"报错：{error_msg}"
                ),
            },
        ],
    )
    if usage_out is not None and getattr(resp, "usage", None):
        usage_out["prompt_tokens"] = resp.usage.prompt_tokens
        usage_out["completion_tokens"] = resp.usage.completion_tokens
        usage_out["window"] = [start + 1, end]

    patch = json.loads(resp.choices[0].message.content or "{}")
    s = int(patch.get("start_line") or 0)
    e = int(patch.get("end_line") or 0)
    replacement = str(patch.get("replacement") or "")

    if not s or not e:
        raise ValueError("模型判定这段代码没问题（未给出补丁）")
    if not (start + 1 <= s <= e <= end):
        raise ValueError(f"补丁行号越界（{s}-{e} 不在 {start + 1}-{end} 内）")
    new_lines = replacement.splitlines()
    if not new_lines:
        raise ValueError("补丁内容为空")
    if len(new_lines) > 25 or (e - s + 1) > 25:
        raise ValueError("补丁范围过大，改走整份修复")

    merged_lines = list(lines)
    merged_lines[s - 1 : e] = new_lines
    merged = "\n".join(merged_lines)

    if abs(merged.count("{") - merged.count("}")) > 3:
        raise ValueError("拼接后括号不平衡，改走整份修复")
    return merged
