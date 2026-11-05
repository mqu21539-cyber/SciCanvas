# -*- coding: utf-8 -*-
"""模板：阻尼单摆（简谐振动 + 阻尼衰减）。"""
from . import controls_html, metrics_html

META = {
    "name": "oscillator",
    "title": "阻尼单摆：简谐振动与衰减",
    "category": "经典力学 / 振动",
    "formula": "θ'' = −(g/L)·sinθ − c·θ'",
    "controls": [
        {"id": "L", "label": "摆长 L", "unit": "m", "min": 0.2, "max": 3.0, "step": 0.05, "default": 1.0},
        {"id": "c", "label": "阻尼系数 c", "unit": "1/s", "min": 0.0, "max": 1.2, "step": 0.02, "default": 0.05},
        {"id": "g", "label": "重力加速度 g", "unit": "m/s²", "min": 1.0, "max": 25.0, "step": 0.1, "default": 9.8},
    ],
    "metrics": [
        {"id": "T", "label": "理论周期 T", "color": "text-cyan-400"},
        {"id": "E", "label": "机械能 E", "color": "text-emerald-400"},
        {"id": "th", "label": "摆角 θ", "color": "text-amber-400"},
        {"id": "regime", "label": "状态", "color": "text-rose-400", "initial": "自由摆动"},
    ],
}

_JS = r"""
(function(){
  const P = window.__SCICANVAS__;
  const cv = document.getElementById('scene');
  const ctx = cv.getContext('2d');
  const wrap = document.getElementById('wrap');
  const btnPause = document.getElementById('btnPause');
  const btnReset = document.getElementById('btnReset');

  const els = {}, vals = {};
  P.controls.forEach(function(c){
    els[c.id] = document.getElementById(c.id);
    vals[c.id] = document.getElementById('val_' + c.id);
  });

  let W = 800, H = 500, DPR = 1;
  function resize(){
    const r = wrap.getBoundingClientRect();
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.max(320, r.width);
    H = Math.max(220, r.height);
    cv.width = Math.floor(W * DPR);
    cv.height = Math.floor(H * DPR);
    cv.style.width = W + 'px';
    cv.style.height = H + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  window.addEventListener('resize', resize);
  resize();

  const S = { L: 1, c: 0.05, g: 9.8, th: 0.7, om: 0, t: 0, run: true, trail: [] };

  function readParams(){
    S.L = parseFloat(els.L.value);
    S.c = parseFloat(els.c.value);
    S.g = parseFloat(els.g.value);
    vals.L.textContent = S.L.toFixed(2);
    vals.c.textContent = S.c.toFixed(2);
    vals.g.textContent = S.g.toFixed(1);
  }

  function reset(){
    S.th = 0.7; S.om = 0; S.t = 0; S.trail = []; S.run = true;
    btnPause.textContent = '暂停';
    readParams();
  }

  Object.keys(els).forEach(function(k){ els[k].addEventListener('input', readParams); });
  btnPause.addEventListener('click', function(){
    S.run = !S.run;
    btnPause.textContent = S.run ? '暂停' : '继续';
    btnPause.classList.toggle('bg-amber-600', !S.run);
  });
  btnReset.addEventListener('click', reset);

  // 半隐式欧拉，固定步长，保证不同帧率下轨迹一致
  function step(dt){
    const alpha = -(S.g / S.L) * Math.sin(S.th) - S.c * S.om;
    S.om += alpha * dt;
    S.th += S.om * dt;
    S.t += dt;
  }

  function geometry(){
    const pxPerM = (H * 0.62) / 3.0;
    const r = Math.min(S.L * pxPerM, H * 0.62);
    return { px: W / 2, py: H * 0.18, r: r };
  }

  var acc = 0, last = performance.now();
  const FIXED = 1 / 480;

  function loop(now){
    let dt = (now - last) / 1000;
    last = now;
    if (dt > 0.1) dt = 0.1;
    if (S.run){
      acc += dt;
      while (acc >= FIXED){ step(FIXED); acc -= FIXED; }
    }
    render();
    requestAnimationFrame(loop);
  }

  function render(){
    const g = geometry();
    const bx = g.px + Math.sin(S.th) * g.r;
    const by = g.py + Math.cos(S.th) * g.r;

    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#0b1220');
    bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, W, H);

    // 网格
    ctx.strokeStyle = 'rgba(56,189,248,0.05)';
    ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 48){ ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 48){ ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

    // 平衡位置虚线
    ctx.save();
    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = 'rgba(148,163,184,0.25)';
    ctx.beginPath();
    ctx.moveTo(g.px, g.py);
    ctx.lineTo(g.px, g.py + g.r + 24);
    ctx.stroke();
    ctx.restore();

    // 轨迹
    if (S.run){
      S.trail.push([bx, by]);
      if (S.trail.length > 240) S.trail.shift();
    }
    ctx.save();
    ctx.lineWidth = 1.4;
    for (let i = 1; i < S.trail.length; i++){
      const a = (i / S.trail.length) * 0.5;
      ctx.strokeStyle = 'rgba(168,85,247,' + a.toFixed(3) + ')';
      ctx.beginPath();
      ctx.moveTo(S.trail[i-1][0], S.trail[i-1][1]);
      ctx.lineTo(S.trail[i][0], S.trail[i][1]);
      ctx.stroke();
    }
    ctx.restore();

    // 支架 + 摆杆
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(g.px - 42, g.py); ctx.lineTo(g.px + 42, g.py); ctx.stroke();

    ctx.strokeStyle = '#94a3b8';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(g.px, g.py); ctx.lineTo(bx, by); ctx.stroke();

    // 摆球
    ctx.save();
    ctx.shadowBlur = 18;
    ctx.shadowColor = '#38bdf8';
    ctx.fillStyle = '#38bdf8';
    ctx.beginPath(); ctx.arc(bx, by, 11, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    // 角度标注
    ctx.save();
    ctx.strokeStyle = 'rgba(251,191,36,0.75)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(g.px, g.py, 52, Math.PI / 2, Math.PI / 2 + S.th, S.th < 0);
    ctx.stroke();
    ctx.restore();

    // 指标
    const T = 2 * Math.PI * Math.sqrt(S.L / S.g);
    const E = 0.5 * S.L * S.L * S.om * S.om + S.g * S.L * (1 - Math.cos(S.th));
    const setTxt = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };
    setTxt('m_T', T.toFixed(2) + ' s');
    setTxt('m_E', E.toFixed(2) + ' J/kg');
    setTxt('m_th', (S.th * 180 / Math.PI).toFixed(1) + '°');

    // 阻尼状态判定
    const w0 = Math.sqrt(S.g / S.L);
    let regime = '欠阻尼';
    if (S.c >= 2 * w0) regime = '过阻尼';
    else if (Math.abs(S.c - 2 * w0) < 0.05) regime = '临界阻尼';
    else if (S.c === 0) regime = '无阻尼（理想）';
    setTxt('m_regime', regime);
  }

  reset();
  requestAnimationFrame(loop);
})();
"""


def build(params, copy):
    """params: 参数覆盖；copy: 文案（title/subtitle/challenge）。"""
    body = (
        '<div class="max-w-7xl mx-auto p-4 lg:p-6">'
        '<header class="mb-4">'
        f'<h1 class="text-2xl lg:text-3xl font-bold tracking-tight">{copy["title"]}</h1>'
        f'<p class="text-slate-400 text-sm mt-1">{copy["subtitle"]}</p>'
        f'<p class="text-slate-500 text-xs mt-2 font-mono">{copy["formula"]}</p>'
        "</header>"
        '<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">'
        '<div class="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-3">'
        '<div class="flex items-center justify-between mb-2 px-1">'
        '<span class="text-xs uppercase tracking-widest text-slate-500">仿真视窗</span>'
        '<div class="flex gap-2">'
        '<button id="btnPause" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">暂停</button>'
        '<button id="btnReset" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">重置</button>'
        "</div></div>"
        '<div id="wrap" class="relative w-full rounded-lg overflow-hidden" style="aspect-ratio:16/10">'
        '<canvas id="scene" class="w-full h-full"></canvas>'
        "</div></div>"
        '<div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col gap-4">'
        '<div><h2 class="text-sm font-semibold text-slate-200 mb-3">控制面板</h2>'
        '<div class="space-y-4">' + controls_html(META, params) + "</div></div>"
        '<div class="border-t border-slate-800 pt-3"><h2 class="text-sm font-semibold text-slate-200 mb-3">实时数据</h2>'
        '<div class="grid grid-cols-2 gap-2">' + metrics_html(META) + "</div></div>"
        '<div class="mt-auto text-[11px] text-slate-500 leading-relaxed bg-slate-950/40 rounded-lg p-2.5 border border-slate-800">'
        f'<span class="text-slate-400 font-semibold">🤯 直觉挑战：</span>{copy["challenge"]}'
        "</div></div></div></div>"
        "<script>" + _JS + "</script>"
    )
    return body