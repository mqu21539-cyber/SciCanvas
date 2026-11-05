# -*- coding: utf-8 -*-
"""模板：洛伦兹吸引子与蝴蝶效应（双轨对比）。"""
from . import controls_html, metrics_html

META = {
    "name": "lorenz",
    "title": "洛伦兹吸引子：0.0001 的偏差如何撕裂两条轨道",
    "category": "混沌 / 非线性动力学",
    "formula": "ẋ=σ(y−x), ẏ=x(ρ−z)−y, ż=xy−βz",
    "controls": [
        {"id": "sigma", "label": "σ（普朗特数）", "min": 4, "max": 20, "step": 0.5, "default": 10},
        {"id": "rho", "label": "ρ（瑞利数）", "min": 10, "max": 45, "step": 0.5, "default": 28},
        {"id": "beta", "label": "β（几何因子）", "min": 1, "max": 4, "step": 0.1, "default": 2.67},
        {"id": "eps", "label": "初始偏差 ε", "unit": "×10⁻⁴", "min": 1, "max": 100, "step": 1, "default": 1},
    ],
    "metrics": [
        {"id": "sep", "label": "两轨距离", "color": "text-rose-400"},
        {"id": "t", "label": "演化时间", "color": "text-cyan-400"},
        {"id": "state", "label": "状态", "color": "text-amber-400", "initial": "同步"},
        {"id": "hs", "label": "步长", "color": "text-emerald-400"},
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
  const S = { sigma: 10, rho: 28, beta: 2.67, eps: 1e-4, t: 0, run: true, a: null, b: null, ta: [], tb: [] };

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
    S.sigma = parseFloat(els.sigma.value);
    S.rho = parseFloat(els.rho.value);
    S.beta = parseFloat(els.beta.value);
    S.eps = parseFloat(els.eps.value) * 1e-4;
    vals.sigma.textContent = S.sigma.toFixed(1);
    vals.rho.textContent = S.rho.toFixed(1);
    vals.beta.textContent = S.beta.toFixed(2);
    vals.eps.textContent = (S.eps * 1e4).toFixed(0);
  }

  function reset(){
    read();
    S.a = { x: 1, y: 1, z: 1 };
    S.b = { x: 1 + S.eps, y: 1, z: 1 };
    S.t = 0; S.ta = []; S.tb = []; S.run = true;
    btnPause.textContent = '暂停';
  }

  // RK4 一步
  function deriv(p){
    return {
      dx: S.sigma * (p.y - p.x),
      dy: p.x * (S.rho - p.z) - p.y,
      dz: p.x * p.y - S.beta * p.z,
    };
  }
  function rk4(p, dt){
    const k1 = deriv(p);
    const k2 = deriv({ x: p.x + k1.dx * dt / 2, y: p.y + k1.dy * dt / 2, z: p.z + k1.dz * dt / 2 });
    const k3 = deriv({ x: p.x + k2.dx * dt / 2, y: p.y + k2.dy * dt / 2, z: p.z + k2.dz * dt / 2 });
    const k4 = deriv({ x: p.x + k3.dx * dt, y: p.y + k3.dy * dt, z: p.z + k3.dz * dt });
    return {
      x: p.x + (dt / 6) * (k1.dx + 2 * k2.dx + 2 * k3.dx + k4.dx),
      y: p.y + (dt / 6) * (k1.dy + 2 * k2.dy + 2 * k3.dy + k4.dy),
      z: p.z + (dt / 6) * (k1.dz + 2 * k2.dz + 2 * k3.dz + k4.dz),
    };
  }

  function toScreen(x, z){
    // 世界范围：x ∈ [-25, 25]，z ∈ [0, 55]
    const sx = W / 56, sz = H / 62;
    return { x: W / 2 + x * sx, y: H - 24 - z * sz };
  }

  function draw(){
    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#050b18'); bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    function path(arr, color, width, alpha){
      if (arr.length < 2) return;
      ctx.beginPath();
      for (let i = 0; i < arr.length; i++){
        const p = toScreen(arr[i].x, arr[i].z);
        i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
      }
      ctx.strokeStyle = color;
      ctx.globalAlpha = alpha;
      ctx.lineWidth = width;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    path(S.ta, '#38bdf8', 1.3, 0.85);
    path(S.tb, '#f43f5e', 1.3, 0.85);

    if (S.a){
      const pa = toScreen(S.a.x, S.a.z);
      const pb = toScreen(S.b.x, S.b.z);
      ctx.save();
      ctx.shadowBlur = 14; ctx.shadowColor = '#38bdf8';
      ctx.fillStyle = '#38bdf8';
      ctx.beginPath(); ctx.arc(pa.x, pa.y, 4.5, 0, Math.PI * 2); ctx.fill();
      ctx.shadowColor = '#f43f5e'; ctx.fillStyle = '#f43f5e';
      ctx.beginPath(); ctx.arc(pb.x, pb.y, 4.5, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }

    ctx.fillStyle = 'rgba(148,163,184,0.65)';
    ctx.font = '11px ui-monospace, monospace';
    ctx.fillText('投影：x–z 平面  ·  蓝/红 = 初值相差 ε 的两条轨道', 12, 20);
  }

  function metrics(){
    const dx = S.a.x - S.b.x, dy = S.a.y - S.b.y, dz = S.a.z - S.b.z;
    const sep = Math.hypot(dx, dy, dz);
    const set = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };
    set('m_sep', sep < 1e-6 ? '0' : sep.toFixed(4));
    set('m_t', S.t.toFixed(1));
    set('m_state', sep > 1 ? '已完全分离（混沌）' : sep > 1e-3 ? '正在指数分离' : '同步');
    set('m_hs', '0.004');
  }

  var last = performance.now(), acc = 0;
  const DT = 0.004;
  function loop(now){
    let dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (S.run && S.a && S.b){
      acc += dt * 26;                       // 时间加速
      let guard = 0;
      while (acc >= DT && guard++ < 400){
        S.a = rk4(S.a, DT);
        S.b = rk4(S.b, DT);
        S.t += DT;
        acc -= DT;
      }
      S.ta.push({ x: S.a.x, z: S.a.z });
      S.tb.push({ x: S.b.x, z: S.b.z });
      if (S.ta.length > 2600){ S.ta.shift(); S.tb.shift(); }
      metrics();
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
        '<span class="text-xs uppercase tracking-widest text-slate-500">相空间投影</span>'
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