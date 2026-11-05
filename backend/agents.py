import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from prompts import CODER_SYSTEM_PROMPT, FIXER_SYSTEM_PROMPT, PLANNER_SYSTEM_PROMPT

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


def generate_lab(user_concept: str) -> dict:
    """Planner -> Coder 双 Agent 流水线"""
    # 1. Planner Agent 生成结构化实验蓝图
    plan_res = get_client().chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": f"请为以下科学概念或论文段落设计2D互动实验：\n{user_concept}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    plan_json_str = plan_res.choices[0].message.content
    plan_data = clean_json_output(plan_json_str)

    # 2. Coder Agent 将蓝图转化为单文件交互式 HTML
    code_res = get_client().chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": CODER_SYSTEM_PROMPT},
            {"role": "user", "content": f"请严格按照以下 JSON 实验蓝图编写单文件 HTML 交互仿真代码：\n{plan_json_str}"},
        ],
        temperature=0.2,
    )
    html_code = clean_html_output(code_res.choices[0].message.content)

    return {"plan": plan_data, "html": html_code}


def fix_lab_code(broken_html: str, error_msg: str) -> str:
    """当沙盒捕获到 JS 运行报错时，自动调用此函数修复"""
    fix_res = get_client().chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": FIXER_SYSTEM_PROMPT},
            {"role": "user", "content": f"运行报错信息：{error_msg}\n\n原HTML代码：\n{broken_html}"},
        ],
        temperature=0.1,
    )
    return clean_html_output(fix_res.choices[0].message.content)
