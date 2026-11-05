# -*- coding: utf-8 -*-
"""模板：中心力场轨道（开普勒问题）。"""
from . import controls_html, metrics_html

META = {
    "name": "orbit",
    "title": "引力轨道：为什么速度一变轨道就变",
    "category": "天体物理 / 轨道力学",
    "formula": "a = −μ·r̂/r² ，E = v²/2 − μ/r",
    "controls": [
        {"id": "mu", "label": "中心质量 μ", "unit": "×10³", "min": 0.5, "max": 5.0, "step": 0.1, "default": 1.0},
        {"id": "r0", "label": "初始距离 r₀", "unit": "×10³ km", "min": 1.5, "max": 6.0, "step": 0.1, "default": 3.0},
        {"id": "vf", "label": "速度倍率 v/v圆", "min": 0.55, "max": 1.45, "step": 0.01, "default": 1.0},
    ],
    "metrics": [
        {"id": "shape", "label": "轨道类型", "color": "text-amber-400", "initial": "圆"},
        {"id": "e", "label": "偏心率 e", "color": "text-cyan-400"},
        {"id": "T", "label": "周期 T", "color": "text-emerald-400"},
        {"id": "r", "label": "当前距离 r", "color": "text-rose-400"},
    ],
}

_JS = r"""
(function(){
  const P = window.__SCICANVAS__;
  const cv = document.getElementById('scene');
  const ctx = cv.getContext('2d');
  const wrap = document.getElementById('wrap');
  const els = {}, vals = {};
  P.controls.forEach(function(c){
    els[c.id] = document.getElementById(c.id);
    vals[c.id] = document.getElementById('val_' + c.id);
  });
  const btnPause = document.getElementById('btnPause');
  const btnReset = document.getElementById('btnReset');

  let W = 800, H = 500, DPR = 1;
  const S = { mu: 1.0, r0: 3.0, vf: 1.0, x: 3, y: 0, vx: 0, vy: 0, t: 0, run: true, trail: [], maxR: 3 };

  function resize(){
    const r = wrap.getBoundingClientRect();
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.max(320, r.width); H = Math.max(220, r.height);
    cv.width = Math.floor(W * DPR); cv.height = Math.floor(H * DPR);
    cv.style.width = W + 'px'; cv.style.height = H + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  window.addEventListener('resize', function(){ resize(); draw(); });
  resize();

  function read(){
    S.mu = parseFloat(els.mu.value);
    S.r0 = parseFloat(els.r0.value);
    S.vf = parseFloat(els.vf.value);
    vals.mu.textContent = S.mu.toFixed(1);
    vals.r0.textContent = S.r0.toFixed(1);
    vals.vf.textContent = S.vf.toFixed(2);
  }

  function reset(){
    read();
    S.x = S.r0; S.y = 0;
    const vc = Math.sqrt(S.mu / S.r0);
    S.vx = 0; S.vy = vc * S.vf;
    S.t = 0; S.trail = []; S.maxR = S.r0 * 1.2; S.run = true;
    btnPause.textContent = '暂停';
    updateMetrics();
  }

  function accel(x, y){
    const r2 = x * x + y * y;
    const r = Math.sqrt(r2);
    const a = -S.mu / (r2 * r);
    return { ax: a * x, ay: a * y };
  }

  function step(dt){
    // 速度 Verlet（辛积分，长时间稳定）
    const a1 = accel(S.x, S.y);
    S.x += S.vx * dt + 0.5 * a1.ax * dt * dt;
    S.y += S.vy * dt + 0.5 * a1.ay * dt * dt;
    const a2 = accel(S.x, S.y);
    S.vx += 0.5 * (a1.ax + a2.ax) * dt;
    S.vy += 0.5 * (a1.ay + a2.ay) * dt;
    S.t += dt;
  }

  function updateMetrics(){
    const r = Math.hypot(S.x, S.y);
    const v2 = S.vx * S.vx + S.vy * S.vy;
    const E = v2 / 2 - S.mu / r;
    const h = S.x * S.vy - S.y * S.vx;
    const e = Math.sqrt(Math.max(0, 1 + (2 * E * h * h) / (S.mu * S.mu)));
    const set = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };

    let shape = '椭圆';
    if (e < 0.02) shape = '圆';
    else if (Math.abs(E) < 2e-3) shape = '抛物线（逃逸临界）';
    else if (E > 0) shape = '双曲线（已逃逸）';

    set('m_shape', shape);
    set('m_e', e < 9 ? e.toFixed(3) : '—');
    if (E < 0) {
      const a = -S.mu / (2 * E);
      set('m_T', (2 * Math.PI * Math.sqrt((a * a * a) / S.mu)).toFixed(2) + ' ×10³s');
    } else {
      set('m_T', '不闭合');
    }
    set('m_r', r.toFixed(2) + ' ×10³km');
  }

  function scale(){
    return Math.min(W, H) * 0.42 / Math.max(S.maxR, 1);
  }

  function toScreen(x, y){
    const s = scale();
    return { x: W / 2 + x * s, y: H / 2 - y * s };
  }

  function draw(){
    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#080f1e'); bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    // 星点背景
    ctx.fillStyle = 'rgba(148,163,184,0.25)';
    for (let i = 0; i < 90; i++){
      const sx = (i * 137.5) % W, sy = (i * 89.7) % H;
      ctx.fillRect(sx, sy, 1.2, 1.2);
    }

    // 中心天体
    const c = toScreen(0, 0);
    const g = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, 26);
    g.addColorStop(0, 'rgba(251,191,36,0.95)');
    g.addColorStop(0.45, 'rgba(251,191,36,0.35)');
    g.addColorStop(1, 'rgba(251,191,36,0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(c.x, c.y, 26, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#fbbf24';
    ctx.beginPath(); ctx.arc(c.x, c.y, 7, 0, Math.PI * 2); ctx.fill();

    // 轨迹
    if (S.trail.length > 1){
      ctx.beginPath();
      for (let i = 0; i < S.trail.length; i++){
        const p = toScreen(S.trail[i][0], S.trail[i][1]);
        i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
      }
      ctx.strokeStyle = 'rgba(56,189,248,0.75)';
      ctx.lineWidth = 1.6;
      ctx.shadowBlur = 8; ctx.shadowColor = 'rgba(56,189,248,0.6)';
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // 探测器
    const p = toScreen(S.x, S.y);
    ctx.save();
    ctx.shadowBlur = 14; ctx.shadowColor = '#a855f7';
    ctx.fillStyle = '#a855f7';
    ctx.beginPath(); ctx.arc(p.x, p.y, 6, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    ctx.fillStyle = 'rgba(148,163,184,0.7)';
    ctx.font = '11px ui-monospace, monospace';
    ctx.fillText('t = ' + S.t.toFixed(1) + ' ×10³s', 12, 20);
    ctx.fillText('尺度 ' + S.maxR.toFixed(1) + ' ×10³km', 12, 36);
  }

  var last = performance.now(), acc = 0;
  const DT = 0.004;
  function loop(now){
    let dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (S.run){
      acc += dt * 40;   // 时间加速，方便观察
      let guard = 0;
      while (acc >= DT && guard++ < 400){ step(DT); acc -= DT; }
      const r = Math.hypot(S.x, S.y);
      if (r > S.maxR) S.maxR = r;
      S.trail.push([S.x, S.y]);
      if (S.trail.length > 1200) S.trail.shift();
      if (r > 60 || r < 0.05){ S.run = false; }
      updateMetrics();
    }
    draw();
    requestAnimationFrame(loop);
  }

  Object.keys(els).forEach(function(k){ els[k].addEventListener('input', reset); });
  btnPause.addEventListener('click', function(){
    S.run = !S.run;
    btnPause.textContent = S.run ? '暂停' : '继续';
  });
  btnReset.addEventListener('click', reset);

  reset();
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
        '<span class="text-xs uppercase tracking-widest text-slate-500">轨道视图</span>'
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