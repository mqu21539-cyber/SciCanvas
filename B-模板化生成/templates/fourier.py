# -*- coding: utf-8 -*-
"""模板：傅里叶级数合成方波。"""
from . import controls_html, metrics_html

META = {
    "name": "fourier",
    "title": "傅里叶级数：用正弦波拼出方波",
    "category": "数学 / 信号分解",
    "formula": "f(t) ≈ (4/π) Σ sin((2k−1)ωt) / (2k−1)",
    "controls": [
        {"id": "n", "label": "谐波项数", "unit": "项", "min": 1, "max": 25, "step": 1, "default": 5},
        {"id": "omega", "label": "角频率 ω", "unit": "rad/s", "min": 0.5, "max": 6, "step": 0.1, "default": 2},
        {"id": "phase", "label": "初相 φ", "unit": "rad", "min": 0, "max": 6.28, "step": 0.1, "default": 0},
    ],
    "metrics": [
        {"id": "terms", "label": "谐波项数", "color": "text-cyan-400"},
        {"id": "overshoot", "label": "吉布斯过冲", "color": "text-rose-400"},
        {"id": "rms", "label": "与方波 RMS 误差", "color": "text-amber-400"},
        {"id": "f", "label": "基频 f", "color": "text-emerald-400"},
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
  const S = { n: 5, omega: 2, phase: 0, t: 0, run: true };

  function resize(){
    const r = wrap.getBoundingClientRect();
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.max(320, r.width); H = Math.max(220, r.height);
    cv.width = Math.floor(W * DPR); cv.height = Math.floor(H * DPR);
    cv.style.width = W + 'px'; cv.style.height = H + 'px';
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  window.addEventListener('resize', function(){ resize(); render(); });
  resize();

  function read(){
    S.n = parseInt(els.n.value, 10);
    S.omega = parseFloat(els.omega.value);
    S.phase = parseFloat(els.phase.value);
    vals.n.textContent = S.n;
    vals.omega.textContent = S.omega.toFixed(1);
    vals.phase.textContent = S.phase.toFixed(2);
  }

  // 傅里叶部分和（奇次谐波）
  function partial(t){
    let s = 0;
    for (let k = 1; k <= S.n; k++){
      const m = 2 * k - 1;
      s += Math.sin(m * S.omega * t + S.phase) / m;
    }
    return (4 / Math.PI) * s;
  }
  function harmonic(t, k){
    const m = 2 * k - 1;
    return (4 / Math.PI) * Math.sin(m * S.omega * t + S.phase) / m;
  }

  const SPAN = 2 * Math.PI;   // 画两个周期

  function toX(t){ return 40 + (t / SPAN) * (W - 80); }
  function toY(v){ return H / 2 - v * (H * 0.32); }

  function render(){
    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#0b1220'); bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    // 目标方波
    ctx.save();
    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = 'rgba(148,163,184,0.45)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let px = 40; px <= W - 40; px += 2){
      const t = ((px - 40) / (W - 80)) * SPAN;
      const v = Math.sin(S.omega * t + S.phase) >= 0 ? 1 : -1;
      px === 40 ? ctx.moveTo(px, toY(v)) : ctx.lineTo(px, toY(v));
    }
    ctx.stroke();
    ctx.restore();

    // 各次谐波
    ctx.globalAlpha = 0.35;
    for (let k = 1; k <= S.n; k++){
      ctx.beginPath();
      for (let i = 0; i <= 200; i++){
        const t = (i / 200) * SPAN;
        const y = toY(harmonic(t, k));
        i === 0 ? ctx.moveTo(toX(t), y) : ctx.lineTo(toX(t), y);
      }
      ctx.strokeStyle = 'rgba(168,85,247,0.55)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // 部分和
    ctx.beginPath();
    for (let i = 0; i <= 400; i++){
      const t = (i / 400) * SPAN;
      const y = toY(partial(t));
      i === 0 ? ctx.moveTo(toX(t), y) : ctx.lineTo(toX(t), y);
    }
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2.4;
    ctx.shadowBlur = 10; ctx.shadowColor = 'rgba(56,189,248,0.6)';
    ctx.stroke();
    ctx.shadowBlur = 0;

    // 指标
    let maxV = 0, sq = 0, N = 600;
    for (let i = 0; i <= N; i++){
      const t = (i / N) * SPAN;
      const v = partial(t);
      if (v > maxV) maxV = v;
      const target = Math.sin(S.omega * t + S.phase) >= 0 ? 1 : -1;
      sq += (v - target) ** 2;
    }
    const set = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };
    set('m_terms', String(S.n));
    // 吉布斯过冲的教科书口径是「占跳变高度的比例」：方波跳变 = 2（−1→1），
    // 所以相对平台幅值的超出量要再除以 2，极限才回到 8.95%
    set('m_overshoot', ((maxV - 1) / 2 * 100).toFixed(1) + ' %');
    set('m_rms', Math.sqrt(sq / (N + 1)).toFixed(3));
    set('m_f', (S.omega / (2 * Math.PI)).toFixed(2) + ' Hz');
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
        '<span class="text-xs uppercase tracking-widest text-slate-500">波形叠加</span>'
        '<div class="flex gap-2">'
        '<button id="btnPause" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">暂停</button>'
        '<button id="btnReset" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">重置</button>'
        "</div></div>"
        '<div id="wrap" class="relative w-full rounded-lg overflow-hidden" style="aspect-ratio:16/10">'
        '<canvas id="scene" class="w-full h-full"></canvas>'
        "</div>"
        '<p class="mt-2 px-1 text-[11px] text-slate-500">虚线＝目标方波　蓝线＝部分和　紫线＝各次谐波</p>'
        "</div>"
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