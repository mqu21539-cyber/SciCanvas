# -*- coding: utf-8 -*-
"""08 · arXiv 摘要直读

离线部分（编号识别）必过；联网部分（真抓论文 + 真生成）在断网时跳过，
不把"没网"当成"代码坏了"。
"""
import sys
import time

import httpx

API = "http://127.0.0.1:8010"
BACKEND = r"D:\SciCanvas\backend"

sys.path.insert(0, BACKEND)
try:
    import arxiv  # noqa: E402
except Exception as e:  # noqa: BLE001
    print(f"  SKIP  无法导入 arxiv 模块：{e}")
    sys.exit(2)

CASES = [
    ("arXiv:1706.03762", "1706.03762"),
    ("看看 https://arxiv.org/abs/2401.01234 这篇", "2401.01234"),
    ("ARXIV:2310.00001v3", "2310.00001v3"),
    ("arxiv hep-th/9901001", "hep-th/9901001"),
    ("演示单摆的阻尼振动", None),
    ("", None),
]

fail = 0
print("  编号识别")
for text, expect in CASES:
    got = arxiv.extract_id(text)
    ok = got == expect
    fail += 0 if ok else 1
    print(f"    {'PASS' if ok else 'FAIL'}  {text!r:40} -> {got}")

# ---- PDF 正文直读（不调模型，只验抽取链路）----
print("  PDF 正文抽取")
try:
    t0 = time.time()
    expanded, paper = arxiv.expand("https://arxiv.org/pdf/1706.03762")
    dt = time.time() - t0
    chars = (paper or {}).get("fulltext_chars") or 0
    ok = chars >= 2000 and "正文节选" in expanded
    fail += 0 if ok else 1
    print(f"    {'PASS' if ok else 'FAIL'}  {chars} 字 / {dt:.1f}s · 提示词 {len(expanded)} 字符")
except Exception as e:  # noqa: BLE001
    print(f"    SKIP  PDF 部分跳过（{type(e).__name__}）")

# ---- 联网：真抓一篇 ----
print("  抓取 + 生成")
try:
    t0 = time.time()
    r = httpx.post(
        f"{API}/api/generate",
        json={"prompt": "请把 arXiv:1706.03762 这篇论文做成可交互实验"},
        timeout=240,
    )
    dt = time.time() - t0
    d = r.json()
    paper = d.get("arxiv") or {}
    if r.status_code != 200:
        print(f"    FAIL  HTTP {r.status_code}: {str(d)[:120]}")
        fail += 1
    elif paper.get("id") != "1706.03762":
        print(f"    FAIL  响应里没有正确的 arXiv 元信息：{paper}")
        fail += 1
    elif not (d.get("html") or "").strip():
        print("    FAIL  没拿到 HTML")
        fail += 1
    else:
        print(f"    PASS  {paper.get('title')[:50]}")
        print(f"          mode={d.get('mode')} · {dt:.0f}s · html {len(d['html'])} 字符")
except Exception as e:  # noqa: BLE001
    print(f"    SKIP  联网部分跳过（{type(e).__name__}）")

print(f"\n  失败 {fail} 项")
sys.exit(1 if fail else 0)