# -*- coding: utf-8 -*-
"""模板：一维热传导（显式差分）。"""
from . import controls_html, metrics_html

META = {
    "name": "heat",
    "title": "一维热传导：温度为什么要「抹平」",
    "category": "热学 / 偏微分方程",
    "formula": "∂u/∂t = α ∂²u/∂x²",
    "controls": [
        {"id": "alpha", "label": "热扩散率 α", "unit": "×10⁻³", "min": 0.1, "max": 2.0, "step": 0.05, "default": 0.6},
        {"id": "width", "label": "初始热区宽度", "unit": "%", "min": 5, "max": 60, "step": 1, "default": 18},
        {"id": "speed", "label": "时间加速", "unit": "×", "min": 1, "max": 12, "step": 1, "default": 4},
    ],
    "metrics": [
        {"id": "t", "label": "已模拟时间", "color": "text-cyan-400"},
        {"id": "max", "label": "最高温度", "color": "text-rose-400"},
        {"id": "total", "label": "总热量（守恒）", "color": "text-emerald-400"},
        {"id": "shape", "label": "分布形态", "color": "text-amber-400", "initial": "尖峰"},
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

  const N = 90;              // 格子数
  const DX = 1 / N;
  let W = 800, H = 500, DPR = 1;
  const S = { alpha: 0.6, width: 18, speed: 4, t: 0, run: true, u: new Float64Array(N), u0: new Float64Array(N) };

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
    S.alpha = parseFloat(els.alpha.value) * 1e-3;
    S.width = parseFloat(els.width.value);
    S.speed = parseFloat(els.speed.value);
    vals.alpha.textContent = (S.alpha * 1e3).toFixed(2);
    vals.width.textContent = S.width.toFixed(0);
    vals.speed.textContent = S.speed.toFixed(0);
  }

  function reset(){
    read();
    S.t = 0;
    const c = (N - 1) / 2;
    const sigma = Math.max(1.2, (S.width / 100) * N * 0.42);
    for (let i = 0; i < N; i++){
      const d = (i - c) / sigma;
      S.u[i] = Math.exp(-0.5 * d * d);   // 高斯热包，峰值 1
    }
    S.u0 = Float64Array.from(S.u);
    btnPause.textContent = '暂停';
  }

  // 显式差分：r = α·dt/dx² 必须 ≤ 0.5 才稳定，这里固定取 0.4
  function step(){
    const r = 0.4;
    const next = new Float64Array(N);
    for (let i = 0; i < N; i++){
      const l = i > 0 ? S.u[i - 1] : S.u[i];           // 绝热边界
      const rr = i < N - 1 ? S.u[i + 1] : S.u[i];
      next[i] = S.u[i] + r * (l - 2 * S.u[i] + rr);
    }
    S.u = next;
    S.t += r * DX * DX / S.alpha * 1000;   // 折算成便于阅读的「毫秒级」时间
  }

  function draw(){
    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#0b1220'); bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    const padL = 56, padR = 24, padT = 40, padB = 48;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    // 热力图条带
    for (let i = 0; i < N; i++){
      const x = padL + (i / N) * plotW;
      const w = plotW / N + 1;
      const v = Math.min(1, S.u[i]);
      const r = Math.round(15 + 240 * v);
      const g = Math.round(23 + 120 * (1 - Math.abs(v - 0.5) * 2));
      const b = Math.round(42 + 200 * (1 - v));
      ctx.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
      ctx.fillRect(x, padT, w, 26);
    }

    // 温度曲线
    ctx.beginPath();
    for (let i = 0; i < N; i++){
      const x = padL + (i / N) * plotW;
      const y = padT + 26 + plotH - S.u[i] * (plotH - 20);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2.2;
    ctx.shadowBlur = 10; ctx.shadowColor = 'rgba(56,189,248,0.45)';
    ctx.stroke();
    ctx.shadowBlur = 0;

    // 坐标框
    ctx.strokeStyle = 'rgba(148,163,184,0.35)';
    ctx.lineWidth = 1;
    ctx.strokeRect(padL, padT + 26, plotW, plotH);

    ctx.fillStyle = 'rgba(148,163,184,0.75)';
    ctx.font = '11px ui-monospace, monospace';
    ctx.fillText('温度分布 u(x)', padL, padT - 12);
    ctx.fillText('0', padL - 6, padT + 26 + plotH + 14);
    ctx.fillText('绝热边界 ↔ 绝热边界', padL + plotW / 2 - 60, H - 12);

    // 指标
    let max = 0, total = 0;
    for (let i = 0; i < N; i++){ max = Math.max(max, S.u[i]); total += S.u[i]; }
    const set = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };
    set('m_t', S.t.toFixed(2));
    set('m_max', max.toFixed(3));
    set('m_total', (total / N).toFixed(4));
    const flat = max < 1.15 / N * 4 ? '几乎均匀' : max < 0.35 ? '正在抹平' : '仍有尖峰';
    set('m_shape', flat);
  }

  var last = performance.now(), acc = 0;
  function loop(now){
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (S.run){
      acc += dt * S.speed * 60;    // 每秒约 60·speed 步
      let guard = 0;
      while (acc >= 1 && guard++ < 400){ step(); acc -= 1; }
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
        '<span class="text-xs uppercase tracking-widest text-slate-500">温度分布</span>'
        '<div class="flex gap-2">'
        '<button id="btnPause" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">暂停</button>'
        '<button id="btnReset" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">重置</button>'
        "</div></div>"
        '<div id="wrap" class="relative w-full rounded-lg overflow-hidden" style="aspect-ratio:16/10">'
        '<canvas id="scene" class="w-full h-full"></canvas>'
        "</div>"
        '<p class="mt-2 px-1 text-[11px] text-slate-500">上方色条＝温度热力图，蓝线＝温度曲线；两端绝热（无热量流出）</p>'
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