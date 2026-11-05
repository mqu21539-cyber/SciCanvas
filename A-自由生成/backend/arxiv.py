# -*- coding: utf-8 -*-
"""arXiv 摘要直读。

用户贴一条 `arXiv:2401.01234` 或 `https://arxiv.org/abs/2401.01234` 时，
后端自己去 arXiv 官方 API 取标题与摘要，再交给生成流水线——不用手动复制正文。
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API = "http://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
TIMEOUT = 8

# 2401.01234 / 2401.01234v2 / hep-th/9901001 这类老编号
_ID_RE = re.compile(
    r"arxiv(?:\.org/(?:abs|pdf)/|:\s*|\s+|/)\s*"
    r"((?:\d{4}\.\d{4,5})(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)",
    re.IGNORECASE,
)


def extract_id(text: str) -> str | None:
    """从一段话里认出 arXiv 编号；认不出返回 None。"""
    if not text:
        return None
    m = _ID_RE.search(text)
    return m.group(1) if m else None


def fetch(arxiv_id: str, timeout: int = TIMEOUT) -> dict | None:
    """取标题与摘要。网络失败返回 None，调用方据此回落到原文。"""
    url = f"{API}?{urllib.parse.urlencode({'id_list': arxiv_id})}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - 固定域名
            raw = resp.read()
    except Exception:  # noqa: BLE001 - 离线/超时都不该阻断生成
        return None

    try:
        root = ET.fromstring(raw)
        entry = root.find(f"{ATOM}entry")
        if entry is None:
            return None
        title = (entry.findtext(f"{ATOM}title") or "").strip()
        summary = (entry.findtext(f"{ATOM}summary") or "").strip()
        if not summary or "Error" in title:
            return None
        return {
            "id": arxiv_id,
            "title": " ".join(title.split()),
            "abstract": " ".join(summary.split()),
            "url": f"https://arxiv.org/abs/{arxiv_id}",
        }
    except ET.ParseError:
        return None


def expand(prompt: str) -> tuple[str, dict | None]:
    """把「含 arXiv 编号的一句话」展开成「标题 + 摘要 + 生成指令」。

    返回 (新提示词, 论文信息)。没认出编号、或抓取失败时原样返回。
    """
    arxiv_id = extract_id(prompt)
    if not arxiv_id:
        return prompt, None

    paper = fetch(arxiv_id)
    if not paper:
        return prompt, None

    expanded = (
        f"论文《{paper['title']}》（arXiv:{arxiv_id}）\n"
        f"摘要：{paper['abstract']}\n\n"
        "请为这篇论文的核心机制设计一个可交互的 2D 实验沙盒。"
    )
    return expanded, paper