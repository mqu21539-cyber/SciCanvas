# -*- coding: utf-8 -*-
"""09 · 全息契约（离线）

验证「模型只写 50 行 JS」这条路的各种边界：合格片段能拼成完整页面，
不合格片段（写成整份 HTML / 漏了 window.frame / 括号不平衡 / 还在用 canvas）
必须被挡住并抛 HoloError —— 因为上层要靠这个信号回落到整份 HTML 生成。
"""
import os
import sys

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "A-自由生成", "backend")
sys.path.insert(0, BACKEND)

import holo_build  # noqa: E402

fail = 0


def check(name, ok, detail=""):
    global fail
    fail += 0 if ok else 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


GOOD_JS = """
(function(){
  var P = HOLO.P;
  var S = { th: 0.5, om: 0 };
  window.reset = function(){ S.th = 0.5; S.om = 0; HOLO.L0('<line x1="0" y1="200" x2="700" y2="200" stroke="#38bdf8"/>'); };
  window.frame = function(dt, t){
    var a = -(P.g / 1.0) * Math.sin(S.th) - 0.05 * S.om;
    S.om += a * dt; S.th += S.om * dt;
    HOLO.L1('<circle cx="' + (350 + S.th * 100) + '" cy="200" r="10" fill="url(#sphere-cyan)"/>');
    HOLO.L2(''); HOLO.L3('');
    HOLO.telemetry(Math.min(1, Math.abs(S.om)), 0.5);
  };
})();
"""

PLAN = {
    "title": "单摆",
    "subtitle": "演示",
    "formula_latex": "theta'' = -(g/L) sin theta",
    "controls": [{"id": "g", "label": "重力", "min": 1, "max": 20, "step": 0.1, "default": 9.8}],
    "metrics": [{"id": "th", "label": "摆角"}],
}

print("  合格片段")
html = holo_build.build(PLAN, GOOD_JS)
check("能拼成完整单文件", html.lstrip().startswith("<!DOCTYPE html>"), f"{len(html)} 字符")
check("包含四层 SVG", all(f'id="{i}"' in html for i in ("l0", "l1", "l2", "l3")))
check("保留自愈契约", "SCICANVAS_ERROR" in html)
check("注入参数规格", '"g"' in html)
check("保留模型 JS", "window.frame" in html)

print("  不合格片段要被挡住")
BAD_CASES = [
    ("写成整份 HTML", "<!DOCTYPE html><html><body>...</body></html>"),
    ("漏了 window.frame", "var x = 1; function nothing(){} " + "// pad " * 30),
    ("自己又跑了循环", "window.frame=function(){requestAnimationFrame(x)};" + "// pad " * 10),
    ("还在用 canvas", "window.frame=function(){document.createElement('canvas')};" + "// pad " * 10),
    ("括号不平衡", "window.frame=function(dt){ if(1){ while(1){ for(;;){ } ; " + "// pad " * 20),
    ("太短", "x"),
]
for name, js in BAD_CASES:
    try:
        holo_build.build(PLAN, js)
        check(name, False, "本该抛 HoloError")
    except holo_build.HoloError as e:
        check(name, True, str(e)[:28])

print("  代码围栏与 <script> 包裹")
fenced = "```js\n" + GOOD_JS + "\n```"
try:
    holo_build.build(PLAN, fenced)
    check("```js 围栏能剥掉", True)
except holo_build.HoloError as e:
    check("```js 围栏能剥掉", False, str(e))
wrapped = "<script>" + GOOD_JS + "</script>"
try:
    holo_build.build(PLAN, wrapped)
    check("<script> 包裹能剥掉", True)
except holo_build.HoloError as e:
    check("<script> 包裹能剥掉", False, str(e))

print("  参数/指标兜底")
ctl = holo_build.normalize_controls(None)
check("没有参数时给一个可用滑块", len(ctl) == 1 and ctl[0]["id"] == "k")
ctl2 = holo_build.normalize_controls(
    [{"id": "bad id!", "min": 5, "max": 1, "default": 99, "label": "x" * 40}]
)
check("非法 id 被替换", ctl2[0]["id"] == "p0", ctl2[0]["id"])
check("min>max 被纠正", ctl2[0]["max"] > ctl2[0]["min"])
check("default 被夹到区间内", ctl2[0]["min"] <= ctl2[0]["default"] <= ctl2[0]["max"])
check("label 被截断", len(ctl2[0]["label"]) <= 18)
mets = holo_build.normalize_metrics([{"id": "v", "label": "速度"}])
check("指标补到 4 个", len(mets) == 4, str(len(mets)))

print(f"\n  失败 {fail} 项")
sys.exit(1 if fail else 0)