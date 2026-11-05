#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""02 · 混合路由测试（需要后端在 127.0.0.1:8000 运行）

验证：模板命中走 B（快）、未命中回落 A（慢）、strategy 强制生效。
"""
import sys
import time

try:
    import httpx
except ImportError:
    print("  SKIP  缺 httpx（用 backend 的 venv 跑）")
    sys.exit(2)

API = "http://127.0.0.1:8000"

try:
    health = httpx.get(f"{API}/api/health", timeout=4).json()
except Exception as e:  # noqa: BLE001
    print(f"  SKIP  后端未运行：{e}")
    sys.exit(2)

# 先清缓存：否则这里测的只是"缓存能不能命中"，测不到真实路由。
try:
    removed = httpx.delete(f"{API}/api/cache", timeout=5).json().get("removed")
    print(f"  已清空缓存 {removed} 条")
except Exception:  # noqa: BLE001
    pass

temps = health.get("templates") or []
print(f"\n02 · 混合路由")
print("─" * 40)
print(f"  后端模板：{', '.join(temps) or '（无）'}")

CASES = [
    ("单摆阻尼", "演示单摆的阻尼振动：可调摆长、阻尼系数和重力加速度", "auto", "template", 15),
    ("抛体", "抛体运动：可调初速度、发射角与空气阻力", "template", "template", 15),
    ("傅里叶", "演示傅里叶级数如何用多个旋转圆叠加合成方波", "auto", "agent", 90),
    ("单摆-强制A", "演示单摆的阻尼振动", "agent", "agent", 90),
]

fail = 0
for name, prompt, strategy, expect, budget in CASES:
    t0 = time.time()
    try:
        r = httpx.post(f"{API}/api/generate", json={"prompt": prompt, "strategy": strategy}, timeout=budget + 60)
        dt = time.time() - t0
        if r.status_code != 200:
            print(f"  FAIL  {name}: HTTP {r.status_code} {r.text[:120]}")
            fail += 1
            continue
        d = r.json()
        mode = d.get("mode")
        good = mode == expect
        fail += 0 if good else 1
        print(f"  {'PASS' if good else 'FAIL'}  {name}: mode={mode}（期望 {expect}）· {dt:.1f}s"
              f" · 模板={d.get('template')} · 置信度={d.get('confidence')}")
    except Exception as e:  # noqa: BLE001
        print(f"  FAIL  {name}: {e}")
        fail += 1

print(f"\n  小计：通过 {len(CASES) - fail} / 失败 {fail}")

# ---- 缓存：同一提示词第二次应命中，且几乎不耗时 ----
name, prompt = CASES[0][0], CASES[0][1]
t0 = time.time()
r = httpx.post(f"{API}/api/generate", json={"prompt": prompt, "strategy": "auto"}, timeout=120)
dt = time.time() - t0
d = r.json()
cached_ok = r.status_code == 200 and d.get("cached") is True
fast_ok = dt < 5
if cached_ok and fast_ok:
    print(f"  PASS  缓存命中：{name} 第二次 {dt:.2f}s（cached={d.get('cached')}）")
else:
    print(f"  FAIL  缓存未生效：{dt:.2f}s cached={d.get('cached')}")
    fail += 1

print(f"\n  总计：通过 {len(CASES) + 1 - fail} / 失败 {fail}")
sys.exit(1 if fail else 0)