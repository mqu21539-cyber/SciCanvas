# -*- coding: utf-8 -*-
"""模板：RC 电路充放电。"""
from . import controls_html, metrics_html

META = {
    "name": "rc",
    "title": "RC 充放电：时间常数 τ 到底有多重要",
    "category": "电路 / 一阶系统",
    "formula": "Vc(t) = V₀(1 − e^{−t/τ}) ，τ = RC",
    "controls": [
        {"id": "R", "label": "电阻 R", "unit": "kΩ", "min": 1, "max": 100, "step": 1, "default": 10},
        {"id": "C", "label": "电容 C", "unit": "µF", "min": 1, "max": 100, "step": 1, "default": 10},
        {"id": "V0", "label": "电源电压 V₀", "unit": "V", "min": 1, "max": 20, "step": 0.5, "default": 5},
    ],
    "metrics": [
        {"id": "tau", "label": "时间常数 τ", "color": "text-cyan-400"},
        {"id": "t63", "label": "到 63.2% 用时", "color": "text-emerald-400"},
        {"id": "v", "label": "当前电压", "color": "text-amber-400"},
        {"id": "pct", "label": "已充到", "color": "text-rose-400"},
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
  const S = { R: 10, C: 10, V0: 5, t: 0, run: true };

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

  function tau(){ return S.R * S.C / 1000; }   // kΩ·µF = ms

  function read(){
    S.R = parseFloat(els.R.value);
    S.C = parseFloat(els.C.value);
    S.V0 = parseFloat(els.V0.value);
    vals.R.textContent = S.R.toFixed(0);
    vals.C.textContent = S.C.toFixed(0);
    vals.V0.textContent = S.V0.toFixed(1);
  }

  function vAt(t){ return S.V0 * (1 - Math.exp(-t / tau())); }

  const TSPAN_FACTOR = 5;   // 画 5τ

  function toX(t){ return 52 + (t / (tau() * TSPAN_FACTOR)) * (W - 92); }
  function toY(v){ return H - 46 - (v / S.V0) * (H - 96); }

  function draw(){
    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#0b1220'); bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    // 网格
    ctx.strokeStyle = 'rgba(56,189,248,0.06)';
    ctx.lineWidth = 1;
    for (let x = 52; x < W - 40; x += 48){ ctx.beginPath(); ctx.moveTo(x, 30); ctx.lineTo(x, H - 46); ctx.stroke(); }
    for (let y = 30; y < H - 46; y += 40){ ctx.beginPath(); ctx.moveTo(52, y); ctx.lineTo(W - 40, y); ctx.stroke(); }

    // 坐标轴
    ctx.strokeStyle = 'rgba(148,163,184,0.4)';
    ctx.beginPath();
    ctx.moveTo(52, H - 46); ctx.lineTo(W - 40, H - 46);
    ctx.moveTo(52, H - 46); ctx.lineTo(52, 30);
    ctx.stroke();

    // 63.2% 与 5τ 参考线
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = 'rgba(34,197,94,0.5)';
    const t63 = tau();
    ctx.beginPath();
    ctx.moveTo(52, toY(S.V0 * 0.632));
    ctx.lineTo(toX(t63), toY(S.V0 * 0.632));
    ctx.lineTo(toX(t63), H - 46);
    ctx.stroke();
    ctx.restore();

    // 电压曲线
    ctx.beginPath();
    const tmax = tau() * TSPAN_FACTOR;
    for (let i = 0; i <= 400; i++){
      const t = (i / 400) * tmax;
      const x = toX(t), y = toY(vAt(t));
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2.4;
    ctx.shadowBlur = 10; ctx.shadowColor = 'rgba(56,189,248,0.5)';
    ctx.stroke();
    ctx.shadowBlur = 0;

    // 当前点
    if (S.t <= tmax){
      const x = toX(S.t), y = toY(vAt(S.t));
      ctx.save();
      ctx.fillStyle = '#fbbf24';
      ctx.shadowBlur = 14; ctx.shadowColor = '#fbbf24';
      ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }

    // 标注
    ctx.fillStyle = 'rgba(148,163,184,0.75)';
    ctx.font = '11px ui-monospace, monospace';
    ctx.fillText('t (ms)', W - 70, H - 26);
    ctx.fillText('Vc (V)', 10, 40);
    for (let k = 1; k <= TSPAN_FACTOR; k++){
      const x = toX(tau() * k);
      ctx.fillText(k + 'τ', x - 8, H - 26);
    }

    const set = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };
    set('m_tau', tau().toFixed(1) + ' ms');
    set('m_t63', tau().toFixed(1) + ' ms');
    set('m_v', vAt(Math.min(S.t, tmax)).toFixed(2) + ' V');
    set('m_pct', ((vAt(Math.min(S.t, tmax)) / S.V0) * 100).toFixed(1) + ' %');
  }

  var last = performance.now();
  function loop(now){
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (S.run){
      S.t += dt * tau();          // 1 秒 ≈ 1τ，看得见
      if (S.t > tau() * TSPAN_FACTOR) S.t = tau() * TSPAN_FACTOR;
    }
    draw();
    requestAnimationFrame(loop);
  }

  Object.keys(els).forEach(function(k){ els[k].addEventListener('input', function(){ read(); draw(); }); });
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
        '<span class="text-xs uppercase tracking-widest text-slate-500">充电曲线</span>'
        '<div class="flex gap-2">'
        '<button id="btnPause" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">暂停</button>'
        '<button id="btnReset" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">重置</button>'
        "</div></div>"
        '<div id="wrap" class="relative w-full rounded-lg overflow-hidden" style="aspect-ratio:16/10">'
        '<canvas id="scene" class="w-full h-full"></canvas>'
        "</div>"
        '<p class="mt-2 px-1 text-[11px] text-slate-500">绿色虚线＝63.2% 与 t = τ；横轴刻度为 1τ…5τ</p>'
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