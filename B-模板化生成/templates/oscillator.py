# -*- coding: utf-8 -*-
"""模板：阻尼单摆（全息 2.5D 版）。

作者只需要写 reset()/frame() 两个函数，其余（四层舞台、示波器、子弹时间、
滤镜、残影、靶向准星）由 holo_shell 提供。
"""
import os
import sys

import holo_shell

META = {
    "name": "oscillator",
    "title": "阻尼单摆：简谐振动与衰减",
    "category": "经典力学 / 振动",
    "formula": "θ'' = −(g/L)·sinθ − c·θ'",
    "controls": [
        {"id": "L", "label": "摆长 L", "unit": "m", "min": 0.2, "max": 3.0, "step": 0.05, "default": 1.0},
        {"id": "c", "label": "阻尼系数 c", "unit": "1/s", "min": 0.0, "max": 1.2, "step": 0.02, "default": 0.05},
        {"id": "g", "label": "重力加速度 g", "unit": "m/s²", "min": 1.0, "max": 25.0, "step": 0.1, "default": 9.8},
    ],
    "metrics": [
        {"id": "T", "label": "理论周期 T"},
        {"id": "E", "label": "机械能 E"},
        {"id": "th", "label": "摆角 θ"},
        {"id": "regime", "label": "状态"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var OX = 350, OY = 84;          // 悬挂点（SVG 坐标系 700x400）
  var S = { th: 0.55, om: 0, trail: [], t: 0 };

  function lenPx(){ return 70 + (P.L / 3.0) * 150; }
  function bob(){
    var L = lenPx();
    return { x: OX + Math.sin(S.th) * L, y: OY + Math.cos(S.th) * L, L: L };
  }

  function baseLayer(){
    var L = lenPx(), b = bob();
    var arc = '';
    for (var deg = -40; deg <= 40; deg += 10) {
      var rad = deg * Math.PI / 180;
      var x1 = OX + Math.sin(rad) * (L + 12), y1 = OY + Math.cos(rad) * (L + 12);
      var x2 = OX + Math.sin(rad) * (L + 22), y2 = OY + Math.cos(rad) * (L + 22);
      arc += '<line x1="' + x1.toFixed(1) + '" y1="' + y1.toFixed(1) + '" x2="' + x2.toFixed(1) +
             '" y2="' + y2.toFixed(1) + '" stroke="rgba(56,189,248,.45)" stroke-width="1.2"/>';
    }
    return (
      '<circle cx="' + OX + '" cy="' + OY + '" r="5" fill="#0ea5e9"/>' +
      '<line x1="' + (OX - 46) + '" y1="' + OY + '" x2="' + (OX + 46) + '" y2="' + OY + '" stroke="#0284c7" stroke-width="3"/>' +
      '<line x1="' + OX + '" y1="' + OY + '" x2="' + OX + '" y2="' + (OY + L + 40) +
        '" stroke="rgba(56,189,248,.28)" stroke-width="1" stroke-dasharray="5 5"/>' +
      '<path d="M ' + (OX - 120) + ' ' + OY + ' A 120 120 0 0 1 ' + (OX + 120) + ' ' + OY +
        '" fill="none" stroke="rgba(56,189,248,.18)" stroke-width="1" stroke-dasharray="3 5"/>' +
      arc
    );
  }

  function hudLayer(b){
    var lock = HOLO.highlight()
      ? '<circle cx="' + b.x.toFixed(1) + '" cy="' + b.y.toFixed(1) + '" r="34" fill="none" ' +
        'stroke="#10b981" stroke-width="1.4" stroke-dasharray="6 4"/>' +
        '<text x="' + (b.x + 40).toFixed(1) + '" y="' + (b.y - 26).toFixed(1) +
        '" fill="#10b981" font-size="10">TARGET: ' + String(HOLO.highlight()).toUpperCase() + '</text>'
      : '';
    return (
      lock +
      '<g transform="translate(24,24)">' +
      '<rect x="0" y="0" width="196" height="74" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="20" fill="#38bdf8" font-size="10" letter-spacing="1.5">PENDULUM TELEMETRY</text>' +
      '<text x="10" y="42" fill="#e0f2fe" font-size="12">θ = ' + (S.th * 180 / Math.PI).toFixed(1) + '°</text>' +
      '<text x="10" y="62" fill="#86efac" font-size="12">ω = ' + S.om.toFixed(2) + ' rad/s</text>' +
      '</g>'
    );
  }

  window.reset = function(){
    S.th = 0.55; S.om = 0; S.trail = []; S.t = 0;
    HOLO.L0(baseLayer());
    HOLO.L1(''); HOLO.L2(''); HOLO.L3('');
  };

  window.frame = function(dt, t){
    var g = P.g, L = P.L, c = P.c;
    var alpha = -(g / Math.max(0.2, L)) * Math.sin(S.th) - c * S.om;
    S.om += alpha * dt;
    S.th += S.om * dt;
    S.t += dt;

    var b = bob();

    // L1：摆线与摆球（拟物渐变球）
    if (dt > 0) {
      S.trail.push(b.x.toFixed(1) + ',' + b.y.toFixed(1));
      if (S.trail.length > 90) S.trail.shift();
    }
    HOLO.L1(
      '<polyline points="' + S.trail.join(' ') + '" fill="none" stroke="rgba(56,189,248,.35)" stroke-width="2"/>' +
      '<line x1="' + OX + '" y1="' + OY + '" x2="' + b.x.toFixed(1) + '" y2="' + b.y.toFixed(1) +
        '" stroke="#7dd3fc" stroke-width="2.4"/>' +
      '<circle cx="' + b.x.toFixed(1) + '" cy="' + b.y.toFixed(1) + '" r="15" fill="url(#sphere-cyan)" filter="url(#neon-glow)"/>'
    );

    // L2：切向速度矢量
    var vx = Math.cos(S.th) * S.om * b.L * 0.28;
    var vy = -Math.sin(S.th) * S.om * b.L * 0.28;
    HOLO.L2(
      '<line x1="' + b.x.toFixed(1) + '" y1="' + b.y.toFixed(1) + '" x2="' + (b.x + vx).toFixed(1) +
        '" y2="' + (b.y + vy).toFixed(1) + '" stroke="#38bdf8" stroke-width="2.4" marker-end="url(#ar-cyan)"/>' +
      '<text x="' + (b.x + vx + 6).toFixed(1) + '" y="' + (b.y + vy - 6).toFixed(1) +
        '" fill="#38bdf8" font-size="11">v</text>'
    );

    HOLO.L3(hudLayer(b));

    // 数据面板 + 示波器
    var T = 2 * Math.PI * Math.sqrt(Math.max(0.2, L) / Math.max(0.1, g));
    var E = 0.5 * L * S.om * S.om + g * L * (1 - Math.cos(S.th));
    HOLO.metric('T', T.toFixed(2) + ' s');
    HOLO.metric('E', E.toFixed(2) + ' J/kg');
    HOLO.metric('th', (S.th * 180 / Math.PI).toFixed(1) + '°');
    var regime = c > 1.6 * Math.sqrt(g / Math.max(0.2, L)) ? '过阻尼'
      : c > 0.98 * Math.sqrt(g / Math.max(0.2, L)) ? '临界阻尼'
      : c > 0.02 ? '欠阻尼' : '无阻尼';
    HOLO.metric('regime', regime);

    HOLO.telemetry(Math.min(1, Math.abs(S.om) / 5), Math.min(1, (1 - Math.cos(S.th)) / 2));
  };
})();
"""


def build(params, copy):
    controls = [
        dict(c, default=params.get(c["id"], c["default"])) for c in META["controls"]
    ]
    spec = {
        "title": copy.get("title", META["title"]),
        "subtitle": copy.get("subtitle", META["category"]),
        "formula": copy.get("formula", META["formula"]),
        "controls": controls,
        "metrics": META["metrics"],
    }
    return holo_shell.render(spec, _JS)