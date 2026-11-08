# -*- coding: utf-8 -*-
"""模板：洛伦兹吸引子（全息 2.5D 版）。"""
from shell import holo_shell

META = {
    "name": "lorenz",
    "title": "洛伦兹吸引子：0.0001 的偏差如何撕裂两条轨道",
    "category": "混沌 / 非线性动力学",
    "formula": "ẋ=σ(y−x), ẏ=x(ρ−z)−y, ż=xy−βz",
    "controls": [
        {"id": "sigma", "label": "σ（普朗特数）", "unit": "", "min": 4, "max": 20, "step": 0.5, "default": 10},
        {"id": "rho", "label": "ρ（瑞利数）", "unit": "", "min": 10, "max": 45, "step": 0.5, "default": 28},
        {"id": "beta", "label": "β（几何因子）", "unit": "", "min": 1, "max": 4, "step": 0.1, "default": 2.67},
        {"id": "eps", "label": "初始偏差 ε", "unit": "×10⁻⁴", "min": 1, "max": 100, "step": 1, "default": 1},
    ],
    "metrics": [
        {"id": "sep", "label": "两轨距离"},
        {"id": "t", "label": "演化时间"},
        {"id": "state", "label": "状态"},
        {"id": "hs", "label": "步长"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var CX = 350, CY = 205, SX = 7.2, SZ = 4.6;   // 3D → 2D（取 x–z 平面，经典蝴蝶形）
  var DT = 0.004, MAXPTS = 1500;
  var A = { x: 0.1, y: 0, z: 20, trail: [] };
  var B = { x: 0.1, y: 0, z: 20, trail: [] };
  var t = 0, warm = 0;

  function proj(x, z){
    return { u: CX + x * SX, v: CY - (z - 25) * SZ };
  }

  function deriv(s){
    return {
      dx: P.sigma * (s.y - s.x),
      dy: s.x * (P.rho - s.z) - s.y,
      dz: s.x * s.y - P.beta * s.z,
    };
  }

  function rk4(s, h){
    var k1 = deriv(s);
    var k2 = deriv({ x: s.x + k1.dx * h / 2, y: s.y + k1.dy * h / 2, z: s.z + k1.dz * h / 2 });
    var k3 = deriv({ x: s.x + k2.dx * h / 2, y: s.y + k2.dy * h / 2, z: s.z + k2.dz * h / 2 });
    var k4 = deriv({ x: s.x + k3.dx * h, y: s.y + k3.dy * h, z: s.z + k3.dz * h });
    s.x += (k1.dx + 2 * k2.dx + 2 * k3.dx + k4.dx) * h / 6;
    s.y += (k1.dy + 2 * k2.dy + 2 * k3.dy + k4.dy) * h / 6;
    s.z += (k1.dz + 2 * k2.dz + 2 * k3.dz + k4.dz) * h / 6;
  }

  window.reset = function(){
    // 直接抓握：在画布里上下拖动，等于拖动「rho」滑块
    if (HOLO.bindDrag) HOLO.bindDrag('rho');
    A = { x: 0.1, y: 0, z: 20, trail: [] };
    B = { x: 0.1 + P.eps * 1e-4, y: 0, z: 20, trail: [] };
    t = 0; warm = 0;

    var g = '';
    for (var i = -30; i <= 30; i += 10) {
      var p = proj(i, 25);
      g += '<line x1="' + p.u + '" y1="20" x2="' + p.u + '" y2="380" stroke="rgba(56,189,248,.05)"/>';
    }
    for (var j = 0; j <= 50; j += 10) {
      var q = proj(0, j);
      g += '<line x1="40" y1="' + q.v + '" x2="660" y2="' + q.v + '" stroke="rgba(56,189,248,.05)"/>';
    }
    HOLO.L0(g);
    HOLO.L1(''); HOLO.L2(''); HOLO.L3('');
  };

  window.frame = function(dt, tGlobal){
    // 预热：先跑掉初始瞬态，画面直接从吸引子上开始
    if (warm < 2200) {
      var n = Math.min(40, 2200 - warm);
      for (var k = 0; k < n; k++) { rk4(A, DT); rk4(B, DT); }
      warm += n;
      return;
    }

    if (dt > 0) {
      var steps = Math.max(1, Math.min(24, Math.round(dt * 900)));
      for (var i = 0; i < steps; i++) { rk4(A, DT); rk4(B, DT); t += DT; }
      var pa = proj(A.x, A.z), pb = proj(B.x, B.z);
      A.trail.push(pa.u.toFixed(1) + ',' + pa.v.toFixed(1));
      B.trail.push(pb.u.toFixed(1) + ',' + pb.v.toFixed(1));
      if (A.trail.length > MAXPTS) A.trail.shift();
      if (B.trail.length > MAXPTS) B.trail.shift();
    }

    var pa = proj(A.x, A.z), pb = proj(B.x, B.z);

    HOLO.L1(
      '<polyline points="' + A.trail.join(' ') + '" fill="none" stroke="rgba(56,189,248,.55)" stroke-width="1.3"/>' +
      '<polyline points="' + B.trail.join(' ') + '" fill="none" stroke="rgba(244,63,94,.5)" stroke-width="1.1" stroke-dasharray="3 2"/>' +
      '<circle cx="' + pa.u.toFixed(1) + '" cy="' + pa.v.toFixed(1) + '" r="4" fill="#38bdf8" filter="url(#neon-glow)"/>' +
      '<circle cx="' + pb.u.toFixed(1) + '" cy="' + pb.v.toFixed(1) + '" r="4" fill="#f43f5e" filter="url(#neon-glow)"/>'
    );

    // 两轨之间的连线：距离越拉越长，是"撕裂"最直观的表达
    var sep = Math.hypot(A.x - B.x, A.y - B.y, A.z - B.z);
    HOLO.L2(
      '<line x1="' + pa.u.toFixed(1) + '" y1="' + pa.v.toFixed(1) + '" x2="' + pb.u.toFixed(1) +
        '" y2="' + pb.v.toFixed(1) + '" stroke="rgba(244,63,94,' + Math.min(0.85, 0.15 + sep / 14) + ')" stroke-width="1.4"/>'
    );

    var state = sep < 0.01 ? '完全同步' : sep < 1 ? '开始分岔' : sep < 8 ? '明显分离' : '彻底撕裂';
    var lock = HOLO.highlight()
      ? '<circle cx="' + pa.u.toFixed(1) + '" cy="' + pa.v.toFixed(1) + '" r="26" fill="none" stroke="#10b981" stroke-width="1.4" stroke-dasharray="6 4"/>'
      : '';
    HOLO.L3(lock +
      '<g transform="translate(24,24)">' +
      '<rect x="0" y="0" width="238" height="76" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="18" fill="#38bdf8" font-size="10" letter-spacing="1.2">CHAOS TELEMETRY</text>' +
      '<text x="10" y="40" fill="#e0f2fe" font-size="12">A (' + A.x.toFixed(1) + ', ' + A.z.toFixed(1) + ')</text>' +
      '<text x="10" y="60" fill="#fda4af" font-size="12">B (' + B.x.toFixed(1) + ', ' + B.z.toFixed(1) + ')</text>' +
      '</g>'
    );

    HOLO.metric('sep', sep.toFixed(3));
    HOLO.metric('t', t.toFixed(1) + ' s');
    HOLO.metric('state', state);
    HOLO.metric('hs', DT.toFixed(3));

    HOLO.telemetry(Math.min(1, sep / 12), Math.min(1, (A.z) / 50));
  };
})();
"""


def build(params, copy):
    controls = [dict(c, default=params.get(c["id"], c["default"])) for c in META["controls"]]
    return holo_shell.render(
        {
            "title": copy.get("title", META["title"]),
            "subtitle": copy.get("subtitle", META["category"]),
            "formula": copy.get("formula", META["formula"]),
            "controls": controls,
            "metrics": META["metrics"],
        },
        _JS,
    )