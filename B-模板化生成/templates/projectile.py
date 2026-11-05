# -*- coding: utf-8 -*-
"""模板：抛体运动（含线性空气阻力，可对比理想抛体）。"""
from . import controls_html, metrics_html

META = {
    "name": "projectile",
    "title": "抛体运动：空气阻力下的真实弹道",
    "category": "经典力学 / 运动学",
    "formula": "a = −k·v − g·ŷ",
    "controls": [
        {"id": "v0", "label": "初速度 v₀", "unit": "m/s", "min": 5, "max": 80, "step": 1, "default": 30},
        {"id": "ang", "label": "发射角 α", "unit": "°", "min": 5, "max": 85, "step": 1, "default": 45},
        {"id": "k", "label": "阻力系数 k", "unit": "1/s", "min": 0.0, "max": 0.6, "step": 0.01, "default": 0.0},
    ],
    "metrics": [
        {"id": "range", "label": "射程 R", "color": "text-cyan-400"},
        {"id": "hmax", "label": "最大高度", "color": "text-emerald-400"},
        {"id": "tof", "label": "飞行时间", "color": "text-amber-400"},
        {"id": "ideal", "label": "理想射程", "color": "text-slate-400"},
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

  const G = 9.8;
  const DT = 0.002;
  let W = 800, H = 500, DPR = 1;
  const S = { pts: [], bbox: null, t: 0, tof: 0, run: true };

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
  window.addEventListener('resize', function(){ resize(); simulate(); });
  resize();

  // 只做一次解析积分：参数变化时重算整条弹道
  function simulate(){
    const v0 = parseFloat(els.v0.value);
    const ang = parseFloat(els.ang.value) * Math.PI / 180;
    const k = parseFloat(els.k.value);
    vals.v0.textContent = v0.toFixed(0);
    vals.ang.textContent = (ang * 180 / Math.PI).toFixed(0);
    vals.k.textContent = k.toFixed(2);

    let x = 0, y = 0;
    let vx = v0 * Math.cos(ang), vy = v0 * Math.sin(ang);
    const pts = [[0, 0]];
    let t = 0, tGround = 0;
    while (t < 60){
      const ax = -k * vx;
      const ay = -G - k * vy;
      vx += ax * DT; vy += ay * DT;
      x += vx * DT; y += vy * DT;
      t += DT;
      if (y >= 0 || t < 0.05){ pts.push([x, y]); }
      if (y < 0 && t > 0.05){ tGround = t; break; }
      if (k === 0 && vy < 0 && y >= 0 && pts.length > 2 && t > 1){ tGround = t; }
    }
    // 回收落到地面的点
    const last = pts[pts.length - 1];
    if (last[1] < 0){
      const prev = pts[pts.length - 2];
      const ratio = prev[1] / (prev[1] - last[1]);
      const gx = prev[0] + (last[0] - prev[0]) * ratio;
      pts[pts.length - 1] = [gx, 0];
    }

    S.pts = pts;
    S.tof = tGround || t;
    S.t = 0;

    let maxX = 0, maxY = 0;
    for (let i = 0; i < pts.length; i++){
      if (pts[i][0] > maxX) maxX = pts[i][0];
      if (pts[i][1] > maxY) maxY = pts[i][1];
    }
    S.bbox = { maxX: Math.max(maxX, 1), maxY: Math.max(maxY, 1) };

    const R = pts[pts.length - 1][0];
    const ideal = (v0 * v0 * Math.sin(2 * ang)) / G;
    const setTxt = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };
    setTxt('m_range', R.toFixed(1) + ' m');
    setTxt('m_hmax', maxY.toFixed(1) + ' m');
    setTxt('m_tof', S.tof.toFixed(2) + ' s');
    setTxt('m_ideal', ideal.toFixed(1) + ' m');

    btnPause.textContent = '暂停';
    S.run = true;
  }

  function worldToScreen(x, y){
    const padX = 56, padY = 48;
    const sx = (W - padX * 2) / S.bbox.maxX;
    const sy = (H - padY * 2) / S.bbox.maxY;
    const s = Math.min(sx, sy);
    return { x: padX + x * s, y: H - padY - y * s, s: s };
  }

  function render(){
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

    // 地面
    const groundY = H - 48;
    ctx.strokeStyle = 'rgba(148,163,184,0.35)';
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(0, groundY); ctx.lineTo(W, groundY); ctx.stroke();

    // 完整弹道（虚线预览）
    if (S.pts.length > 1){
      ctx.save();
      ctx.setLineDash([4, 4]);
      ctx.strokeStyle = 'rgba(56,189,248,0.28)';
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      for (let i = 0; i < S.pts.length; i++){
        const p = worldToScreen(S.pts[i][0], S.pts[i][1]);
        if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
      }
      ctx.stroke();
      ctx.restore();
    }

    // 已飞行的轨迹
    const idx = Math.min(S.pts.length - 1, Math.floor((S.t / Math.max(S.tof, 0.001)) * (S.pts.length - 1)));
    ctx.save();
    ctx.strokeStyle = '#a855f7';
    ctx.lineWidth = 2.2;
    ctx.shadowBlur = 10;
    ctx.shadowColor = 'rgba(168,85,247,0.6)';
    ctx.beginPath();
    for (let i = 0; i <= idx; i++){
      const p = worldToScreen(S.pts[i][0], S.pts[i][1]);
      if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
    ctx.restore();

    // 飞行中的小球
    if (idx >= 0 && idx < S.pts.length){
      const p = worldToScreen(S.pts[idx][0], S.pts[idx][1]);
      ctx.save();
      ctx.shadowBlur = 16;
      ctx.shadowColor = '#fbbf24';
      ctx.fillStyle = '#fbbf24';
      ctx.beginPath(); ctx.arc(p.x, p.y, 7, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }

    // 坐标标注
    ctx.save();
    ctx.fillStyle = 'rgba(148,163,184,0.75)';
    ctx.font = '11px ui-monospace, monospace';
    ctx.fillText('0', 12, groundY - 6);
    ctx.fillText(S.bbox.maxX.toFixed(1) + ' m', W - 84, groundY + 18);
    ctx.fillText(S.bbox.maxY.toFixed(1) + ' m', 12, 18);
    ctx.restore();
  }

  var last = performance.now();
  function loop(now){
    let dt = (now - last) / 1000;
    last = now;
    if (dt > 0.1) dt = 0.1;
    if (S.run){
      S.t += dt;
      if (S.t > S.tof){ S.t = S.tof; S.run = false; btnPause.textContent = '重放'; }
    }
    render();
    requestAnimationFrame(loop);
  }

  Object.keys(els).forEach(function(k){ els[k].addEventListener('input', simulate); });
  btnPause.addEventListener('click', function(){
    if (!S.run && S.t >= S.tof){ S.t = 0; S.run = true; btnPause.textContent = '暂停'; return; }
    S.run = !S.run;
    btnPause.textContent = S.run ? '暂停' : '继续';
  });
  btnReset.addEventListener('click', function(){ simulate(); });

  simulate();
  requestAnimationFrame(loop);
})();
"""


def build(params, copy):
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
        '<span class="text-xs uppercase tracking-widest text-slate-500">弹道视窗</span>'
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