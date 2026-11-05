# -*- coding: utf-8 -*-
"""模板：蒙特卡洛估算 π。"""
from . import controls_html, metrics_html

META = {
    "name": "montecarlo",
    "title": "蒙特卡洛：随机撒点凭什么是 π 的 3.14 倍",
    "category": "概率 / 数值方法",
    "formula": "π ≈ 4 × (落在圆内的点数 / 总点数)",
    "controls": [
        {"id": "rate", "label": "每秒撒点", "unit": "个/s", "min": 200, "max": 20000, "step": 200, "default": 4000},
        {"id": "dotsize", "label": "点大小", "unit": "px", "min": 0.5, "max": 3, "step": 0.1, "default": 1.2},
        {"id": "quadrant", "label": "象限（1=四分之一圆）", "unit": "个", "min": 1, "max": 4, "step": 1, "default": 1},
    ],
    "metrics": [
        {"id": "n", "label": "总点数", "color": "text-cyan-400"},
        {"id": "pi", "label": "π 估计", "color": "text-emerald-400"},
        {"id": "err", "label": "相对误差", "color": "text-amber-400"},
        {"id": "ci", "label": "95% 置信半宽", "color": "text-rose-400"},
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
  const S = { rate: 4000, dotsize: 1.2, quad: 1, n: 0, hit: 0, run: true, pts: [], acc: 0 };

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
    S.rate = parseFloat(els.rate.value);
    S.dotsize = parseFloat(els.dotsize.value);
    S.quad = parseInt(els.quadrant.value, 10);
    vals.rate.textContent = S.rate.toFixed(0);
    vals.dotsize.textContent = S.dotsize.toFixed(1);
    vals.quadrant.textContent = S.quad;
  }

  function reset(){
    read();
    S.n = 0; S.hit = 0; S.pts = []; S.acc = 0;
    btnPause.textContent = '暂停';
  }

  function geom(){
    const pad = 46;
    const size = Math.min(W - pad * 2, H - pad * 2 - 20);
    return { x0: (W - size) / 2, y0: (H - size) / 2 + 10, size: size };
  }

  // 撒 n 个点：落在单位圆内的计入 hit
  function spawn(n){
    for (let i = 0; i < n; i++){
      const x = Math.random(), y = Math.random();
      const inside = (x * x + y * y) <= 1;
      if (inside) S.hit++;
      S.n++;
      // 只保留最近 6000 个用于显示，统计仍然用全量 n/hit
      S.pts.push({ x: x, y: y, in: inside });
      if (S.pts.length > 6000) S.pts.shift();
    }
  }

  function draw(){
    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#0b1220'); bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
    const g = geom();

    // 正方形边界
    ctx.strokeStyle = 'rgba(148,163,184,0.45)';
    ctx.lineWidth = 1.2;
    ctx.strokeRect(g.x0, g.y0, g.size, g.size);

    // 四分之一圆
    ctx.beginPath();
    ctx.arc(g.x0, g.y0 + g.size, g.size, -Math.PI / 2, 0);
    ctx.strokeStyle = 'rgba(56,189,248,0.7)';
    ctx.lineWidth = 1.6;
    ctx.stroke();

    // 点
    for (let i = 0; i < S.pts.length; i++){
      const p = S.pts[i];
      const px = g.x0 + p.x * g.size;
      const py = g.y0 + g.size - p.y * g.size;
      ctx.fillStyle = p.in ? 'rgba(34,197,94,0.55)' : 'rgba(244,63,94,0.4)';
      ctx.fillRect(px, py, S.dotsize, S.dotsize);
    }

    // 指标
    const pi = S.n ? 4 * S.hit / S.n : 0;
    const se = S.n ? Math.sqrt(pi * (4 - pi) / S.n) : 0;
    const set = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };
    set('m_n', S.n.toLocaleString('en-US'));
    set('m_pi', S.n ? pi.toFixed(5) : '—');
    set('m_err', S.n ? (((pi - Math.PI) / Math.PI) * 100).toFixed(3) + ' %' : '—');
    set('m_ci', S.n ? '± ' + (1.96 * se).toFixed(5) : '—');

    ctx.fillStyle = 'rgba(148,163,184,0.7)';
    ctx.font = '11px ui-monospace, monospace';
    ctx.fillText('绿=落在四分之一圆内   红=落在圆外', g.x0, g.y0 - 12);
  }

  var last = performance.now();
  function loop(now){
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (S.run){
      S.acc += dt * S.rate;
      const batch = Math.floor(S.acc);
      if (batch > 0){ spawn(batch); S.acc -= batch; }
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
        '<span class="text-xs uppercase tracking-widest text-slate-500">随机撒点</span>'
        '<div class="flex gap-2">'
        '<button id="btnPause" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">暂停</button>'
        '<button id="btnReset" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">重置</button>'
        "</div></div>"
        '<div id="wrap" class="relative w-full rounded-lg overflow-hidden" style="aspect-ratio:16/10">'
        '<canvas id="scene" class="w-full h-full"></canvas>'
        "</div>"
        '<p class="mt-2 px-1 text-[11px] text-slate-500">画面只显示最近 6000 个点，估计值用的是全部点数</p>'
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