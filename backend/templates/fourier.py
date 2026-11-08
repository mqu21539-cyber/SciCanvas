# -*- coding: utf-8 -*-
"""模板：傅里叶级数合成方波（全息 2.5D 版）。"""
from shell import holo_shell

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
        {"id": "terms", "label": "谐波项数"},
        {"id": "overshoot", "label": "吉布斯过冲"},
        {"id": "rms", "label": "与方波 RMS 误差"},
        {"id": "f", "label": "基频 f"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var X0 = 46, X1 = 654, MID = 200, AMP = 96, SPAN = 2 * Math.PI;
  var t = 0;

  function toX(tt){ return X0 + (tt / SPAN) * (X1 - X0); }
  function toY(v){ return MID - v * AMP; }
  function partial(tt){
    var s = 0;
    for (var k = 1; k <= P.n; k++) {
      var m = 2 * k - 1;
      s += Math.sin(m * P.omega * tt + P.phase) / m;
    }
    return (4 / Math.PI) * s;
  }
  function harmonic(tt, k){
    var m = 2 * k - 1;
    return (4 / Math.PI) * Math.sin(m * P.omega * tt + P.phase) / m;
  }
  function poly(fn, color, width, dash){
    var pts = [];
    for (var i = 0; i <= 300; i++) {
      var tt = (i / 300) * SPAN;
      pts.push(toX(tt).toFixed(1) + ',' + toY(fn(tt)).toFixed(1));
    }
    return '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + color + '" stroke-width="' + width + '"' +
      (dash ? ' stroke-dasharray="' + dash + '"' : '') + '/>';
  }

  window.reset = function(){
    t = 0;
    var g = '<line x1="' + X0 + '" y1="' + MID + '" x2="' + X1 + '" y2="' + MID + '" stroke="rgba(56,189,248,.45)" stroke-width="1.4"/>';
    for (var i = 0; i <= 6; i++) {
      var x = X0 + (i / 6) * (X1 - X0);
      g += '<line x1="' + x + '" y1="90" x2="' + x + '" y2="310" stroke="rgba(56,189,248,.06)"/>';
    }
    // 目标方波（虚线）
    var sq = [];
    for (var px = X0; px <= X1; px += 2) {
      var tt = ((px - X0) / (X1 - X0)) * SPAN;
      var v = Math.sin(P.omega * tt + P.phase) >= 0 ? 1 : -1;
      sq.push(px + ',' + toY(v).toFixed(1));
    }
    g += '<polyline points="' + sq.join(' ') + '" fill="none" stroke="rgba(148,163,184,.45)" stroke-width="1.4" stroke-dasharray="6 5"/>';
    HOLO.L0(g);
    HOLO.L1(''); HOLO.L2(''); HOLO.L3('');
  };

  window.frame = function(dt, tGlobal){
    t += dt;

    // L1：各次谐波（淡淡的紫线）
    var harmonics = '';
    for (var k = 1; k <= Math.min(P.n, 12); k++) {
      harmonics += poly(function(tt){ return harmonic(tt, k); }, 'rgba(168,85,247,.28)', 1);
    }
    HOLO.L1(harmonics);

    // L2：部分和（主角）
    HOLO.L2(
      poly(partial, '#38bdf8', 2.6) +
      '<text x="' + (X1 - 150) + '" y="86" fill="#38bdf8" font-size="10">蓝线 = ' + P.n + ' 项叠加</text>'
    );

    // 指标
    var maxV = 0, sq = 0, N = 400;
    for (var i = 0; i <= N; i++) {
      var tt = (i / N) * SPAN;
      var v = partial(tt);
      if (v > maxV) maxV = v;
      var target = Math.sin(P.omega * tt + P.phase) >= 0 ? 1 : -1;
      sq += (v - target) * (v - target);
    }
    // 教科书的吉布斯过冲 = 超出量 / 跳变高度(2)
    var over = (maxV - 1) / 2;
    var lock = HOLO.highlight()
      ? '<rect x="' + X0 + '" y="90" width="' + (X1 - X0) + '" height="220" fill="none" stroke="#10b981" stroke-dasharray="6 5"/>'
      : '';
    HOLO.L3(lock +
      '<g transform="translate(24,24)">' +
      '<rect x="0" y="0" width="232" height="58" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="18" fill="#38bdf8" font-size="10" letter-spacing="1.2">FOURIER SERIES</text>' +
      '<text x="10" y="40" fill="#e0f2fe" font-size="12">n = ' + P.n + '   ω = ' + P.omega.toFixed(1) + '</text>' +
      '</g>'
    );

    HOLO.metric('terms', String(P.n));
    HOLO.metric('overshoot', (over * 100).toFixed(1) + ' %');
    HOLO.metric('rms', Math.sqrt(sq / (N + 1)).toFixed(3));
    HOLO.metric('f', (P.omega / (2 * Math.PI)).toFixed(2) + ' Hz');

    HOLO.telemetry((partial(SPAN * 0.25) + 1.3) / 2.6, (maxV) / 1.3);
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