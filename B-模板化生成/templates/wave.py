# -*- coding: utf-8 -*-
"""模板：一维行波叠加与驻波。"""
from . import controls_html, metrics_html

META = {
    "name": "wave",
    "title": "两列行波叠加：从行波到驻波",
    "category": "波动学 / 叠加原理",
    "formula": "y = A·sin(kx − ωt) + A·sin(kx − ωt + φ)",
    "controls": [
        {"id": "lam", "label": "波长 λ", "unit": "m", "min": 1.0, "max": 8.0, "step": 0.1, "default": 4.0},
        {"id": "v", "label": "波速 v", "unit": "m/s", "min": 1.0, "max": 20.0, "step": 0.5, "default": 6.0},
        {"id": "phase", "label": "相位差 φ", "unit": "°", "min": 0, "max": 360, "step": 5, "default": 0},
    ],
    "metrics": [
        {"id": "f", "label": "频率 f", "color": "text-cyan-400"},
        {"id": "amp", "label": "合振幅", "color": "text-emerald-400"},
        {"id": "mode", "label": "叠加形态", "color": "text-amber-400", "initial": "行波"},
        {"id": "nodes", "label": "节点数", "color": "text-rose-400"},
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
  const S = { lam: 4, v: 6, phase: 0, t: 0, run: true };

  function resize(){
    const r = wrap.getBoundingClientRect();
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.max(320, r.width); H = Math.max(200, r.height);
    cv.width = Math.floor(W * DPR); cv.height = Math.floor(H * DPR);
    cv.style.width = W + 'px'; cv.style.height = H + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  window.addEventListener('resize', resize); resize();

  function read(){
    S.lam = parseFloat(els.lam.value);
    S.v = parseFloat(els.v.value);
    S.phase = parseFloat(els.phase.value) * Math.PI / 180;
    vals.lam.textContent = S.lam.toFixed(1);
    vals.v.textContent = S.v.toFixed(1);
    vals.phase.textContent = (S.phase * 180 / Math.PI).toFixed(0);
  }

  const WORLD_M = 20;             // 可视窗口 20 m
  function px(x){ return (x / WORLD_M) * W; }
  const AMP = 46;

  function waveY(kind, x, t){
    const k = 2 * Math.PI / S.lam;
    const w = k * S.v;
    const base = Math.sin(k * x - w * t);
    if (kind === 0) return base;
    if (kind === 1) return Math.sin(k * x - w * t + S.phase);
    return base + Math.sin(k * x - w * t + S.phase);
  }

  function line(kind, color, width, alpha){
    const mid = H / 2;
    ctx.beginPath();
    for (let i = 0; i <= W; i += 2){
      const x = (i / W) * WORLD_M;
      const y = mid - waveY(kind, x, S.t) * (kind === 2 ? AMP / 2 : AMP);
      i === 0 ? ctx.moveTo(i, y) : ctx.lineTo(i, y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.globalAlpha = alpha;
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function render(){
    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#0b1220'); bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    const mid = H / 2;
    ctx.strokeStyle = 'rgba(148,163,184,0.28)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, mid); ctx.lineTo(W, mid); ctx.stroke();

    // 波长标尺
    const lamPx = px(S.lam);
    ctx.strokeStyle = 'rgba(34,197,94,0.55)';
    ctx.beginPath();
    ctx.moveTo(px(1), mid + AMP * 1.5); ctx.lineTo(px(1) + lamPx, mid + AMP * 1.5);
    ctx.moveTo(px(1), mid + AMP * 1.5 - 5); ctx.lineTo(px(1), mid + AMP * 1.5 + 5);
    ctx.moveTo(px(1) + lamPx, mid + AMP * 1.5 - 5); ctx.lineTo(px(1) + lamPx, mid + AMP * 1.5 + 5);
    ctx.stroke();
    ctx.fillStyle = 'rgba(134,239,172,0.85)';
    ctx.font = '11px ui-monospace, monospace';
    ctx.fillText('λ = ' + S.lam.toFixed(1) + ' m', px(1) + 6, mid + AMP * 1.5 - 8);

    line(0, '#38bdf8', 1.6, 0.55);
    line(1, '#a855f7', 1.6, 0.55);
    line(2, '#22c55e', 2.6, 1);

    // 指标
    const f = S.v / S.lam;
    const amp = 2 * Math.abs(Math.cos(S.phase / 2));
    const isStanding = Math.abs(Math.sin(S.phase)) < 0.05;
    const nodes = isStanding ? Math.floor(WORLD_M / (S.lam / 2)) : 0;
    const set = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };
    set('m_f', f.toFixed(2) + ' Hz');
    set('m_amp', amp.toFixed(2) + ' A');
    set('m_mode', isStanding ? (S.phase < 0.1 ? '同相行波' : '驻波') : '一般叠加');
    set('m_nodes', isStanding && S.phase > 0.1 ? String(nodes) : '—');
  }

  var last = performance.now();
  function loop(now){
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (S.run) S.t += dt;
    render();
    requestAnimationFrame(loop);
  }

  Object.keys(els).forEach(function(k){ els[k].addEventListener('input', read); });
  btnPause.addEventListener('click', function(){
    S.run = !S.run;
    btnPause.textContent = S.run ? '暂停' : '继续';
  });
  btnReset.addEventListener('click', function(){ S.t = 0; S.run = true; btnPause.textContent = '暂停'; read(); });

  read();
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
        '<span class="text-xs uppercase tracking-widest text-slate-500">波形视窗</span>'
        '<div class="flex gap-2">'
        '<button id="btnPause" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">暂停</button>'
        '<button id="btnReset" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">重置</button>'
        "</div></div>"
        '<div id="wrap" class="relative w-full rounded-lg overflow-hidden" style="aspect-ratio:16/10">'
        '<canvas id="scene" class="w-full h-full"></canvas>'
        "</div>"
        '<div class="mt-2 flex gap-4 px-1 text-[11px] text-slate-400">'
        '<span>— 波 1</span><span class="text-purple-400">— 波 2</span><span class="text-emerald-400">— 合成波</span>'
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