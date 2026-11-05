# -*- coding: utf-8 -*-
"""模板：一维热传导（全息 2.5D 版）。"""
import holo_shell

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
        {"id": "t", "label": "已模拟时间"},
        {"id": "max", "label": "最高温度"},
        {"id": "total", "label": "总热量（守恒）"},
        {"id": "shape", "label": "分布形态"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var N = 60, X0 = 60, X1 = 650, BASE = 330, TOP = 70, BAR = (650 - 60) / 60;
  var S = { u: new Float64Array(N), t: 0, acc: 0 };

  function resetField(){
    var c = (N - 1) / 2;
    var sigma = Math.max(1.2, (P.width / 100) * N * 0.42);
    for (var i = 0; i < N; i++) {
      var d = (i - c) / sigma;
      S.u[i] = Math.exp(-0.5 * d * d);
    }
    S.t = 0; S.acc = 0;
  }

  function step(){
    var r = 0.4, next = new Float64Array(N);
    for (var i = 0; i < N; i++) {
      var l = i > 0 ? S.u[i - 1] : S.u[i];
      var rr = i < N - 1 ? S.u[i + 1] : S.u[i];
      next[i] = S.u[i] + r * (l - 2 * S.u[i] + rr);
    }
    S.u = next;
    S.t += 0.002;
  }

  window.reset = function(){
    resetField();
    var g = '<line x1="' + X0 + '" y1="' + BASE + '" x2="' + X1 + '" y2="' + BASE + '" stroke="#0284c7" stroke-width="2"/>' +
      '<line x1="' + X0 + '" y1="' + BASE + '" x2="' + X0 + '" y2="' + TOP + '" stroke="#0284c7" stroke-width="2"/>' +
      '<text x="' + (X0 - 44) + '" y="' + (TOP - 8) + '" fill="#38bdf8" font-size="10">温度 u</text>' +
      '<text x="' + (X1 - 90) + '" y="' + (BASE + 18) + '" fill="rgba(148,163,184,.7)" font-size="10">绝热边界 ⇄</text>';
    for (var j = 0; j <= 4; j++) {
      var y = BASE - (j / 4) * (BASE - TOP);
      g += '<line x1="' + X0 + '" y1="' + y + '" x2="' + X1 + '" y2="' + y + '" stroke="rgba(56,189,248,.07)"/>';
    }
    HOLO.L0(g);
    HOLO.L1(''); HOLO.L2(''); HOLO.L3('');
  };

  function color(v){
    // 蓝 → 青 → 黄 → 红 的伪热力色
    var r = Math.round(30 + 225 * Math.min(1, v * 1.15));
    var gg = Math.round(40 + 150 * Math.min(1, 1 - Math.abs(v - 0.55) * 1.6));
    var b = Math.round(90 + 150 * Math.max(0, 1 - v * 1.6));
    return 'rgb(' + r + ',' + gg + ',' + b + ')';
  }

  window.frame = function(dt, tGlobal){
    if (dt > 0) {
      S.acc += dt * P.speed * 26;
      var guard = 0;
      while (S.acc >= 1 && guard++ < 260) { step(); S.acc -= 1; }
    }

    var bars = '', pts = [], max = 0, total = 0;
    for (var i = 0; i < N; i++) {
      var v = Math.min(1, S.u[i]);
      max = Math.max(max, v); total += v;
      var x = X0 + i * BAR;
      var h = v * (BASE - TOP);
      bars += '<rect x="' + x.toFixed(1) + '" y="' + (BASE - h).toFixed(1) + '" width="' + (BAR - 1).toFixed(1) +
        '" height="' + h.toFixed(1) + '" fill="' + color(v) + '" opacity="0.85"/>';
      pts.push((X0 + i * BAR + BAR / 2).toFixed(1) + ',' + (BASE - h).toFixed(1));
    }

    HOLO.L1(bars);
    HOLO.L2('<polyline points="' + pts.join(' ') + '" fill="none" stroke="#e0f2fe" stroke-width="1.6" filter="url(#neon-glow)"/>');

    var lock = HOLO.highlight()
      ? '<rect x="' + X0 + '" y="' + TOP + '" width="' + (X1 - X0) + '" height="' + (BASE - TOP) + '" fill="none" stroke="#10b981" stroke-dasharray="6 5"/>'
      : '';
    HOLO.L3(lock +
      '<g transform="translate(430,24)">' +
      '<rect x="0" y="0" width="236" height="58" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="18" fill="#38bdf8" font-size="10" letter-spacing="1.2">HEAT TELEMETRY</text>' +
      '<text x="10" y="40" fill="#e0f2fe" font-size="12">t = ' + S.t.toFixed(2) + '   u_max = ' + max.toFixed(3) + '</text>' +
      '</g>'
    );

    var shape = max > 0.75 ? '仍有尖峰' : max > 0.3 ? '正在抹平' : '接近均匀';
    HOLO.metric('t', S.t.toFixed(2));
    HOLO.metric('max', max.toFixed(3));
    HOLO.metric('total', (total / N).toFixed(4));
    HOLO.metric('shape', shape);

    HOLO.telemetry(max, total / N);
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