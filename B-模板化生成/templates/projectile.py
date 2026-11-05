# -*- coding: utf-8 -*-
"""模板：抛体运动（全息 2.5D 版）。"""
import holo_shell

META = {
    "name": "projectile",
    "title": "抛体运动：空气阻力下的真实弹道",
    "category": "经典力学 / 运动学",
    "formula": "a = −k·v − g·ŷ",
    "controls": [
        {"id": "v0", "label": "初速度 v₀", "unit": "m/s", "min": 5, "max": 80, "step": 1, "default": 30},
        {"id": "ang", "label": "发射角 α", "unit": "°", "min": 5, "max": 85, "step": 1, "default": 45},
        {"id": "k", "label": "阻力系数 k", "unit": "1/s", "min": 0.0, "max": 0.6, "step": 0.01, "default": 0.0},
    ],
    "metrics": [
        {"id": "range", "label": "射程 R"},
        {"id": "hmax", "label": "最大高度"},
        {"id": "tof", "label": "飞行时间"},
        {"id": "ideal", "label": "理想射程"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var G = 9.8, SCALE = 3.2, OX = 70, OY = 340;
  var S = { x: 0, y: 0, vx: 0, vy: 0, trail: [], t: 0, hmax: 0, done: false };

  function px(x){ return OX + x * SCALE; }
  function py(y){ return OY - y * SCALE; }

  function launch(){
    var a = P.ang * Math.PI / 180;
    S.x = 0; S.y = 0;
    S.vx = P.v0 * Math.cos(a);
    S.vy = P.v0 * Math.sin(a);
    S.trail = []; S.t = 0; S.hmax = 0; S.done = false;
  }

  function baseLayer(){
    var g = '';
    for (var i = 0; i <= 100; i += 10) {
      g += '<line x1="' + px(i) + '" y1="20" x2="' + px(i) + '" y2="' + OY + '" stroke="rgba(56,189,248,.07)"/>';
      g += '<text x="' + (px(i) - 8) + '" y="' + (OY + 14) + '" fill="rgba(148,163,184,.55)" font-size="9">' + i + '</text>';
    }
    for (var j = 0; j <= 80; j += 10) {
      g += '<line x1="' + OX + '" y1="' + py(j) + '" x2="' + px(100) + '" y2="' + py(j) + '" stroke="rgba(56,189,248,.07)"/>';
      g += '<text x="' + (OX - 26) + '" y="' + (py(j) + 3) + '" fill="rgba(148,163,184,.55)" font-size="9">' + j + '</text>';
    }
    return g +
      '<line x1="' + OX + '" y1="' + OY + '" x2="' + px(100) + '" y2="' + OY + '" stroke="#0284c7" stroke-width="2"/>' +
      '<line x1="' + OX + '" y1="' + OY + '" x2="' + OX + '" y2="20" stroke="#0284c7" stroke-width="2"/>' +
      '<text x="' + (px(92)) + '" y="' + (OY + 26) + '" fill="#38bdf8" font-size="10">x (m)</text>' +
      '<text x="' + (OX - 34) + '" y="34" fill="#38bdf8" font-size="10">y (m)</text>';
  }

  window.reset = function(){
    launch();
    HOLO.L0(baseLayer());
    HOLO.L1(''); HOLO.L2(''); HOLO.L3('');
  };

  window.frame = function(dt, t){
    if (dt > 0 && !S.done) {
      var sp = Math.hypot(S.vx, S.vy);
      var ax = -P.k * sp * S.vx;
      var ay = -G - P.k * sp * S.vy;
      S.vx += ax * dt; S.vy += ay * dt;
      S.x += S.vx * dt; S.y += S.vy * dt;
      S.t += dt;
      if (S.y > S.hmax) S.hmax = S.y;
      S.trail.push(px(S.x).toFixed(1) + ',' + py(S.y).toFixed(1));
      if (S.y < 0) { S.done = true; S.y = 0; }
    }

    var bx = px(S.x), by = py(S.y);

    // L1：弹道轨迹 + 弹体
    HOLO.L1(
      '<polyline points="' + S.trail.join(' ') + '" fill="none" stroke="rgba(56,189,248,.45)" stroke-width="2"/>' +
      '<circle cx="' + bx.toFixed(1) + '" cy="' + by.toFixed(1) + '" r="9" fill="url(#sphere-amber)" filter="url(#neon-glow)"/>'
    );

    // L2：速度矢量与分量
    var vs = 0.55;
    HOLO.L2(
      '<line x1="' + bx.toFixed(1) + '" y1="' + by.toFixed(1) + '" x2="' + (bx + S.vx * vs).toFixed(1) +
        '" y2="' + (by - S.vy * vs).toFixed(1) + '" stroke="#38bdf8" stroke-width="2.2" marker-end="url(#ar-cyan)"/>' +
      '<line x1="' + bx.toFixed(1) + '" y1="' + by.toFixed(1) + '" x2="' + (bx + S.vx * vs * 0.6).toFixed(1) +
        '" y2="' + by.toFixed(1) + '" stroke="rgba(56,189,248,.5)" stroke-width="1.6" stroke-dasharray="4 3"/>' +
      '<line x1="' + bx.toFixed(1) + '" y1="' + by.toFixed(1) + '" x2="' + bx.toFixed(1) +
        '" y2="' + (by - S.vy * vs * 0.6).toFixed(1) + '" stroke="rgba(245,158,11,.6)" stroke-width="1.6" stroke-dasharray="4 3"/>'
    );

    var lock = HOLO.highlight()
      ? '<circle cx="' + bx.toFixed(1) + '" cy="' + by.toFixed(1) + '" r="26" fill="none" stroke="#10b981" stroke-width="1.4" stroke-dasharray="5 4"/>'
      : '';

    // L3：遥测面板
    HOLO.L3(lock +
      '<g transform="translate(414,26)">' +
      '<rect x="0" y="0" width="252" height="86" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="18" fill="#38bdf8" font-size="10" letter-spacing="1.2">PROJECTILE TELEMETRY</text>' +
      '<text x="10" y="40" fill="#e0f2fe" font-size="12">v = ' + Math.hypot(S.vx, S.vy).toFixed(1) + ' m/s</text>' +
      '<text x="10" y="60" fill="#86efac" font-size="12">x = ' + S.x.toFixed(1) + ' m   y = ' + S.y.toFixed(1) + ' m</text>' +
      '<text x="10" y="78" fill="#fbbf24" font-size="12">t = ' + S.t.toFixed(2) + ' s</text>' +
      '</g>'
    );

    var ideal = (P.v0 * P.v0 * Math.sin(2 * P.ang * Math.PI / 180)) / G;
    HOLO.metric('range', S.x.toFixed(1) + ' m');
    HOLO.metric('hmax', S.hmax.toFixed(1) + ' m');
    HOLO.metric('tof', S.t.toFixed(2) + ' s');
    HOLO.metric('ideal', ideal.toFixed(1) + ' m');

    HOLO.telemetry(Math.min(1, S.x / 90), Math.min(1, S.y / 50));
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