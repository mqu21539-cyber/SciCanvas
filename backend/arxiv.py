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


def fetch_fulltext(arxiv_id: str, timeout: int = 20, limit: int = 6000) -> str:
    """下载 PDF 并抽出正文（截断到 limit 字符）。

    摘要只有 200 词，模型经常抓不住真正的机制；PDF 正文能让它看懂公式与实验设置。
    任何一步失败都返回空串，调用方照旧用摘要——这条链路永远不能阻断生成。
    """
    try:
        import io

        from pypdf import PdfReader  # noqa: PLC0415
    except Exception:  # noqa: BLE001 - 没装就静默降级
        return ""

    url = f"https://arxiv.org/pdf/{arxiv_id}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SciCanvas/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - 固定域名
            raw = resp.read(8_000_000)
    except Exception:  # noqa: BLE001
        return ""

    try:
        reader = PdfReader(io.BytesIO(raw))
        chunks: list[str] = []
        total = 0
        for page in reader.pages[:6]:
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            # 参考文献之后的东西对生成实验没用
            cut = text.find("References")
            if cut > 0:
                text = text[:cut]
            chunks.append(text)
            total += len(text)
            if total >= limit:
                break
        body = "\n".join(chunks)
        return " ".join(body.split())[:limit]
    except Exception:  # noqa: BLE001 - 加密/损坏的 PDF
        return ""


def expand(prompt: str, want_fulltext: bool | None = None) -> tuple[str, dict | None]:
    """把「含 arXiv 编号的一句话」展开成「标题 + 摘要 + 生成指令」。

    返回 (新提示词, 论文信息)。没认出编号、或抓取失败时原样返回。
    `want_fulltext` 为 None 时，只要提示词里给了 /pdf/ 链接就自动抓正文。
    """
    arxiv_id = extract_id(prompt)
    if not arxiv_id:
        return prompt, None

    paper = fetch(arxiv_id)
    if not paper:
        return prompt, None

    if want_fulltext is None:
        want_fulltext = "/pdf/" in prompt.lower()

    body = ""
    if want_fulltext:
        body = fetch_fulltext(arxiv_id)
        if body:
            paper = {**paper, "fulltext_chars": len(body)}

    expanded = (
        f"论文《{paper['title']}》（arXiv:{arxiv_id}）\n"
        f"摘要：{paper['abstract']}\n"
    )
    if body:
        expanded += f"\n正文节选（前 {len(body)} 字，来自 PDF）：\n{body}\n"
    expanded += "\n请为这篇论文的核心机制设计一个可交互的 2D 实验沙盒。"
    return expanded, paper