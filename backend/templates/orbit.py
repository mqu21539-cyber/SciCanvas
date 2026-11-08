# -*- coding: utf-8 -*-
"""模板：引力轨道（全息 2.5D 版）。"""
from shell import holo_shell

META = {
    "name": "orbit",
    "title": "引力轨道：为什么速度一变轨道就变",
    "category": "天体物理 / 轨道力学",
    "formula": "a = −μ·r̂/r² ，E = v²/2 − μ/r",
    "controls": [
        {"id": "mu", "label": "中心质量 μ", "unit": "×10³", "min": 0.5, "max": 5.0, "step": 0.1, "default": 1.0},
        {"id": "r0", "label": "初始距离 r₀", "unit": "×10³ km", "min": 1.5, "max": 6.0, "step": 0.1, "default": 3.0},
        {"id": "vf", "label": "速度倍率 v/v圆", "unit": "", "min": 0.55, "max": 1.45, "step": 0.01, "default": 1.0},
    ],
    "metrics": [
        {"id": "shape", "label": "轨道类型"},
        {"id": "e", "label": "偏心率 e"},
        {"id": "T", "label": "周期 T"},
        {"id": "r", "label": "当前距离 r"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var CX = 350, CY = 200, K = 26;               // 1 单位 = 26 像素
  var S = { x: 0, y: 0, vx: 0, vy: 0, trail: [], t: 0, muK: 100 };

  function start(){
    var r0 = P.r0;
    var mu = P.mu * 100;                         // 归一化引力常数
    S.muK = mu;
    S.x = r0; S.y = 0;
    var vc = Math.sqrt(mu / r0);                 // 圆轨道速度
    S.vx = 0; S.vy = vc * P.vf;
    S.trail = []; S.t = 0;
  }

  window.reset = function(){
    start();
    var g = '<circle cx="' + CX + '" cy="' + CY + '" r="3" fill="rgba(56,189,248,.6)"/>';
    for (var rr = 40; rr <= 200; rr += 40) {
      g += '<circle cx="' + CX + '" cy="' + CY + '" r="' + rr + '" fill="none" stroke="rgba(56,189,248,.08)"/>';
    }
    g += '<line x1="60" y1="' + CY + '" x2="640" y2="' + CY + '" stroke="rgba(56,189,248,.1)"/>' +
         '<line x1="' + CX + '" y1="20" x2="' + CX + '" y2="380" stroke="rgba(56,189,248,.1)"/>';
    HOLO.L0(g);
    HOLO.L1(''); HOLO.L2(''); HOLO.L3('');
  };

  window.frame = function(dt, t){
    if (dt > 0) {
      var steps = 6, h = dt / steps;
      for (var i = 0; i < steps; i++) {
        var r2 = S.x * S.x + S.y * S.y;
        var r = Math.sqrt(r2) || 1;
        var a = -S.muK / (r2 * r);
        S.vx += a * S.x * h;
        S.vy += a * S.y * h;
        S.x += S.vx * h;
        S.y += S.vy * h;
      }
      S.t += dt;
      S.trail.push((CX + S.x * K).toFixed(1) + ',' + (CY - S.y * K).toFixed(1));
      if (S.trail.length > 2400) S.trail.shift();
    }

    var px = CX + S.x * K, py = CY - S.y * K;

    HOLO.L1(
      '<polyline points="' + S.trail.join(' ') + '" fill="none" stroke="rgba(56,189,248,.5)" stroke-width="1.6"/>' +
      '<circle cx="' + CX + '" cy="' + CY + '" r="11" fill="url(#sphere-amber)" filter="url(#neon-glow)"/>' +
      '<circle cx="' + px.toFixed(1) + '" cy="' + py.toFixed(1) + '" r="6" fill="url(#sphere-cyan)" filter="url(#neon-glow)"/>'
    );

    var vs = 26;
    HOLO.L2(
      '<line x1="' + px.toFixed(1) + '" y1="' + py.toFixed(1) + '" x2="' + (px + S.vx * vs).toFixed(1) +
        '" y2="' + (py - S.vy * vs).toFixed(1) + '" stroke="#38bdf8" stroke-width="2" marker-end="url(#ar-cyan)"/>' +
      '<line x1="' + px.toFixed(1) + '" y1="' + py.toFixed(1) + '" x2="' + (CX + (px - CX) * 0.35).toFixed(1) +
        '" y2="' + (CY + (py - CY) * 0.35).toFixed(1) + '" stroke="rgba(245,158,11,.55)" stroke-width="1.6" ' +
        'stroke-dasharray="5 4" marker-end="url(#ar-amber)"/>'
    );

    var r = Math.hypot(S.x, S.y);
    var v2 = S.vx * S.vx + S.vy * S.vy;
    var energy = v2 / 2 - S.muK / r;
    var e = Math.sqrt(Math.max(0, 1 + 2 * energy * r * r / S.muK));
    var shape = e > 1 ? '双曲线（逃逸）' : e > 0.75 ? '高椭圆' : e > 0.15 ? '椭圆' : '近圆';
    var period = e < 1 ? 2 * Math.PI * Math.sqrt(Math.pow(P.r0, 3) / S.muK) : Infinity;

    var lock = HOLO.highlight()
      ? '<circle cx="' + px.toFixed(1) + '" cy="' + py.toFixed(1) + '" r="24" fill="none" stroke="#10b981" stroke-width="1.4" stroke-dasharray="6 4"/>'
      : '';
    HOLO.L3(lock +
      '<g transform="translate(400,24)">' +
      '<rect x="0" y="0" width="266" height="76" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="18" fill="#38bdf8" font-size="10" letter-spacing="1.2">ORBITAL TELEMETRY</text>' +
      '<text x="10" y="40" fill="#e0f2fe" font-size="12">r = ' + r.toFixed(2) + '   v = ' + Math.sqrt(v2).toFixed(2) + '</text>' +
      '<text x="10" y="60" fill="#86efac" font-size="12">E = ' + energy.toFixed(3) + '</text>' +
      '</g>'
    );

    HOLO.metric('shape', shape);
    HOLO.metric('e', e < 1 ? e.toFixed(3) : '≥1');
    HOLO.metric('T', isFinite(period) ? period.toFixed(1) + ' s' : '不闭合');
    HOLO.metric('r', r.toFixed(2));

    HOLO.telemetry(Math.min(1, r / 8), Math.min(1, Math.abs(energy) / 2));
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