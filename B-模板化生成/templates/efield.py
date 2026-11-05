# -*- coding: utf-8 -*-
"""模板：两个点电荷的电场线与库仑力。"""
from . import controls_html, metrics_html

META = {
    "name": "efield",
    "title": "双点电荷：电场线与库仑力",
    "category": "电磁学 / 静电场",
    "formula": "E = k·q/r² · r̂ ，F = k·q₁q₂/r²",
    "controls": [
        {"id": "q1", "label": "电荷 q₁", "unit": "nC", "min": -5, "max": 5, "step": 0.5, "default": 2},
        {"id": "q2", "label": "电荷 q₂", "unit": "nC", "min": -5, "max": 5, "step": 0.5, "default": -2},
        {"id": "d", "label": "间距 d", "unit": "m", "min": 1.0, "max": 6.0, "step": 0.1, "default": 3.0},
    ],
    "metrics": [
        {"id": "force", "label": "相互作用", "color": "text-amber-400", "initial": "—"},
        {"id": "F", "label": "库仑力 |F|", "color": "text-cyan-400"},
        {"id": "E0", "label": "中点场强", "color": "text-emerald-400"},
        {"id": "null", "label": "零场点", "color": "text-rose-400"},
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
  const btnReset = document.getElementById('btnReset');

  let W = 800, H = 500, DPR = 1;
  const S = { q1: 2, q2: -2, d: 3 };

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

  const K = 9;   // 归一化常数（q 用 nC，d 用 m，只关心形状与相对大小）

  function read(){
    S.q1 = parseFloat(els.q1.value);
    S.q2 = parseFloat(els.q2.value);
    S.d = parseFloat(els.d.value);
    vals.q1.textContent = S.q1.toFixed(1);
    vals.q2.textContent = S.q2.toFixed(1);
    vals.d.textContent = S.d.toFixed(1);
  }

  function PX(){ return Math.min(W / (S.d * 2.4), H / 4.2); }   // 每米像素
  function toScreen(x, y){ return { x: W / 2 + x * PX(), y: H / 2 - y * PX() }; }

  function charges(){
    return [
      { x: -S.d / 2, y: 0, q: S.q1 },
      { x: S.d / 2, y: 0, q: S.q2 },
    ];
  }

  function fieldAt(x, y){
    let ex = 0, ey = 0;
    for (const c of charges()){
      const dx = x - c.x, dy = y - c.y;
      const r2 = dx * dx + dy * dy;
      if (r2 < 1e-6) continue;
      const r = Math.sqrt(r2);
      const e = K * c.q / r2;
      ex += e * dx / r; ey += e * dy / r;
    }
    return { ex: ex, ey: ey };
  }

  function traceLine(x, y, dir){
    const pts = [[x, y]];
    const step = 0.035;
    for (let i = 0; i < 420; i++){
      const f = fieldAt(x, y);
      const mag = Math.hypot(f.ex, f.ey);
      if (mag < 1e-9) break;
      x += dir * step * f.ex / mag;
      y += dir * step * f.ey / mag;
      pts.push([x, y]);
      let near = false;
      for (const c of charges()){ if (Math.hypot(x - c.x, y - c.y) < 0.06) near = true; }
      if (near) break;
      if (Math.abs(x) > S.d * 3 || Math.abs(y) > S.d * 3) break;
    }
    return pts;
  }

  function drawLine(pts, sign){
    if (pts.length < 2) return;
    ctx.beginPath();
    for (let i = 0; i < pts.length; i++){
      const p = toScreen(pts[i][0], pts[i][1]);
      i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
    }
    ctx.strokeStyle = sign > 0 ? 'rgba(248,113,113,0.55)' : 'rgba(96,165,250,0.55)';
    ctx.lineWidth = 1.2;
    ctx.stroke();
  }

  function draw(){
    ctx.clearRect(0, 0, W, H);
    const bg = ctx.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, '#0b1220'); bg.addColorStop(1, '#0f172a');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);

    // 网格
    ctx.strokeStyle = 'rgba(56,189,248,0.05)';
    for (let x = 0; x < W; x += 48){ ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 48){ ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

    // 电场线：从每个电荷周围均匀播种
    for (const c of charges()){
      if (c.q === 0) continue;
      const dir = c.q > 0 ? 1 : -1;
      const N = 14;
      for (let i = 0; i < N; i++){
        const a = (i / N) * Math.PI * 2;
        const r0 = 0.08;
        const pts = traceLine(c.x + Math.cos(a) * r0, c.y + Math.sin(a) * r0, dir);
        drawLine(pts, c.q);
      }
    }

    // 电荷本体
    for (const c of charges()){
      const p = toScreen(c.x, c.y);
      const rad = 7 + Math.min(Math.abs(c.q), 5) * 1.8;
      ctx.save();
      ctx.shadowBlur = 16;
      ctx.shadowColor = c.q >= 0 ? '#f87171' : '#60a5fa';
      ctx.fillStyle = c.q >= 0 ? '#f87171' : '#60a5fa';
      ctx.beginPath(); ctx.arc(p.x, p.y, rad, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
      ctx.fillStyle = '#0b1220';
      ctx.font = 'bold 12px ui-monospace, monospace';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(c.q >= 0 ? '+' : '–', p.x, p.y + 0.5);
      ctx.textAlign = 'start'; ctx.textBaseline = 'alphabetic';
    }

    // 指标
    const set = function(id, v){ const el = document.getElementById(id); if (el) el.textContent = v; };
    const prod = S.q1 * S.q2;
    set('m_force', Math.abs(S.q1) < 1e-9 || Math.abs(S.q2) < 1e-9 ? '无（有电荷为 0）'
      : prod < 0 ? '吸引' : '排斥');
    set('m_F', (K * Math.abs(prod) / (S.d * S.d)).toFixed(2) + ' k·nC²/m²');
    const mid = fieldAt(0, 0);
    set('m_E0', Math.hypot(mid.ex, mid.ey).toFixed(2) + ' k·nC/m²');

    // 零场点（共线情形解析解）
    let nullTxt = '—';
    if (Math.abs(S.q1) > 1e-9 && Math.abs(S.q2) > 1e-9 && prod > 0){
      const ratio = Math.sqrt(Math.abs(S.q1) / Math.abs(S.q2));
      const x = (-S.d / 2 + ratio * S.d / 2) / (1 + ratio); // 在两者之间
      const outside = Math.abs(S.q1) === Math.abs(S.q2);
      nullTxt = outside ? '无（等量同号，无零点）' : 'x = ' + x.toFixed(2) + ' m（两电荷之间）';
    }
    set('m_null', nullTxt);
  }

  Object.keys(els).forEach(function(k){ els[k].addEventListener('input', function(){ read(); draw(); }); });
  btnReset.addEventListener('click', function(){
    els.q1.value = 2; els.q2.value = -2; els.d.value = 3;
    read(); draw();
  });

  read();
  draw();
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
        '<span class="text-xs uppercase tracking-widest text-slate-500">电场视图</span>'
        '<div class="flex gap-2">'
        '<button id="btnReset" class="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 transition">重置</button>'
        "</div></div>"
        '<div id="wrap" class="relative w-full rounded-lg overflow-hidden" style="aspect-ratio:16/10">'
        '<canvas id="scene" class="w-full h-full"></canvas>'
        "</div>"
        '<p class="mt-2 px-1 text-[11px] text-slate-500">红线：从正电荷出发的电场线；蓝线：指向负电荷的电场线（密度≈场强）</p>'
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