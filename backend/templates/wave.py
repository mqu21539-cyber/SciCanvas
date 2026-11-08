# -*- coding: utf-8 -*-
"""模板：两列行波叠加（全息 2.5D 版）。"""
from shell import holo_shell

META = {
    "name": "wave",
    "title": "两列行波叠加：从行波到驻波",
    "category": "波动学 / 叠加原理",
    "formula": "y = A·sin(kx − ωt) + A·sin(kx − ωt + φ)",
    "controls": [
        {"id": "lam", "label": "波长 λ", "unit": "m", "min": 1.0, "max": 8.0, "step": 0.1, "default": 4.0},
        {"id": "v", "label": "波速 v", "unit": "m/s", "min": 1.0, "max": 20.0, "step": 0.5, "default": 6.0},
        {"id": "phase", "label": "相位差 φ", "unit": "°", "min": 0, "max": 360, "step": 5, "default": 0},
    ],
    "metrics": [
        {"id": "f", "label": "频率 f"},
        {"id": "amp", "label": "合振幅"},
        {"id": "mode", "label": "叠加形态"},
        {"id": "nodes", "label": "节点数"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var X0 = 40, X1 = 660, MID = 200, AMP = 92;
  var S = { t: 0 };

  function k(){ return 2 * Math.PI / Math.max(0.5, P.lam); }
  function w(){ return 2 * Math.PI * P.v / Math.max(0.5, P.lam); }
  function ph(){ return P.phase * Math.PI / 180; }

  // 横向铺 10 米
  function toX(x){ return X0 + (x / 10) * (X1 - X0); }
  function toY(y){ return MID - y * AMP; }

  function curve(fn, color, width, dash){
    var pts = [];
    for (var i = 0; i <= 220; i++) {
      var x = (i / 220) * 10;
      pts.push(toX(x).toFixed(1) + ',' + toY(fn(x)).toFixed(1));
    }
    return '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + color +
      '" stroke-width="' + width + '"' + (dash ? ' stroke-dasharray="' + dash + '"' : '') + '/>';
  }

  window.reset = function(){
    // 直接抓握：在画布里上下拖动，等于拖动「lam」滑块
    if (HOLO.bindDrag) HOLO.bindDrag('lam');
    S.t = 0;
    var g = '';
    for (var i = 0; i <= 10; i++) {
      g += '<line x1="' + toX(i) + '" y1="60" x2="' + toX(i) + '" y2="340" stroke="rgba(56,189,248,.07)"/>';
      g += '<text x="' + (toX(i) - 3) + '" y="352" fill="rgba(148,163,184,.6)" font-size="9">' + i + '</text>';
    }
    g += '<line x1="' + X0 + '" y1="' + MID + '" x2="' + X1 + '" y2="' + MID + '" stroke="rgba(56,189,248,.5)" stroke-width="1.4"/>';
    HOLO.L0(g);
    HOLO.L1(''); HOLO.L2(''); HOLO.L3('');
  };

  window.frame = function(dt, t){
    S.t += dt;
    var kk = k(), ww = w(), pp = ph();
    var A = 0.5;

    function y1(x){ return A * Math.sin(kk * x - ww * S.t); }
    function y2(x){ return A * Math.sin(kk * x - ww * S.t + pp); }
    function ys(x){ return y1(x) + y2(x); }

    HOLO.L1(
      curve(y1, 'rgba(168,85,247,.55)', 1.6) +
      curve(y2, 'rgba(16,185,129,.55)', 1.6)
    );

    HOLO.L2(
      curve(ys, '#38bdf8', 2.6) +
      '<text x="' + (X1 - 96) + '" y="76" fill="#38bdf8" font-size="10">合成为蓝色</text>'
    );

    var lock = HOLO.highlight()
      ? '<circle cx="' + MID + '" cy="' + MID + '" r="0" fill="none"/>' +
        '<rect x="' + X0 + '" y="60" width="' + (X1 - X0) + '" height="280" fill="none" stroke="#10b981" stroke-dasharray="6 5"/>'
      : '';

    HOLO.L3(lock +
      '<g transform="translate(30,26)">' +
      '<rect x="0" y="0" width="228" height="64" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="18" fill="#38bdf8" font-size="10" letter-spacing="1.2">WAVE TELEMETRY</text>' +
      '<text x="10" y="40" fill="#e0f2fe" font-size="12">k = ' + (kk).toFixed(2) + '  ω = ' + ww.toFixed(2) + '</text>' +
      '<text x="10" y="58" fill="#86efac" font-size="12">φ = ' + P.phase.toFixed(0) + '°</text>' +
      '</g>'
    );

    var cfg = 2 * A * Math.abs(Math.cos(pp / 2));   // 合成振幅
    var nodes = Math.round((10 / Math.max(0.5, P.lam)) * 2);
    var mode = Math.abs(Math.cos(pp / 2)) < 0.12 ? '驻波（全消）'
      : Math.abs(Math.sin(pp / 2)) < 0.12 ? '同相叠加（行波）' : '部分相消';
    HOLO.metric('f', (P.v / Math.max(0.5, P.lam)).toFixed(2) + ' Hz');
    HOLO.metric('amp', cfg.toFixed(2) + ' (×A)');
    HOLO.metric('mode', mode);
    HOLO.metric('nodes', mode === '同相叠加（行波）' ? '0' : String(nodes));

    HOLO.telemetry((ys(6.2) + 1) / 2, (y1(6.2) + 0.5) / 1);
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