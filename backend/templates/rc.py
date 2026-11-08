# -*- coding: utf-8 -*-
"""模板：RC 充放电（全息 2.5D 版）。"""
from shell import holo_shell

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
        {"id": "tau", "label": "时间常数 τ"},
        {"id": "t63", "label": "到 63.2% 用时"},
        {"id": "v", "label": "当前电压"},
        {"id": "pct", "label": "已充到"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var X0 = 56, X1 = 650, Y0 = 330, Y1 = 60;
  var S = { t: 0 };
  var SPAN_TAU = 5;                     // 横轴画 5τ

  function tau(){ return P.R * P.C / 1000; }   // kΩ·µF = ms
  function vAt(t){ return P.V0 * (1 - Math.exp(-t / tau())); }
  function toX(t){ return X0 + (t / (tau() * SPAN_TAU)) * (X1 - X0); }
  function toY(v){ return Y0 - (v / Math.max(0.1, P.V0)) * (Y0 - Y1); }

  window.reset = function(){
    // 直接抓握：在画布里上下拖动，等于拖动「R」滑块
    if (HOLO.bindDrag) HOLO.bindDrag('R');
    S.t = 0;
    var g = '';
    for (var k = 1; k <= SPAN_TAU; k++) {
      var x = toX(tau() * k);
      g += '<line x1="' + x + '" y1="' + Y1 + '" x2="' + x + '" y2="' + Y0 + '" stroke="rgba(56,189,248,.08)"/>' +
           '<text x="' + (x - 8) + '" y="' + (Y0 + 16) + '" fill="rgba(148,163,184,.65)" font-size="10">' + k + 'τ</text>';
    }
    g += '<line x1="' + X0 + '" y1="' + Y0 + '" x2="' + X1 + '" y2="' + Y0 + '" stroke="#0284c7" stroke-width="2"/>' +
         '<line x1="' + X0 + '" y1="' + Y0 + '" x2="' + X0 + '" y2="' + Y1 + '" stroke="#0284c7" stroke-width="2"/>' +
         '<text x="' + (X0 - 40) + '" y="' + (Y1 - 6) + '" fill="#38bdf8" font-size="10">Vc</text>';
    // 曲线本身是确定的，放在基准层，避免每帧重画
    var pts = [];
    for (var i = 0; i <= 200; i++) {
      var t = (i / 200) * tau() * SPAN_TAU;
      pts.push(toX(t).toFixed(1) + ',' + toY(vAt(t)).toFixed(1));
    }
    g += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="rgba(56,189,248,.35)" stroke-width="1.6"/>';
    // 63.2% 参考线
    g += '<line x1="' + X0 + '" y1="' + toY(P.V0 * 0.632) + '" x2="' + toX(tau()) + '" y2="' + toY(P.V0 * 0.632) +
      '" stroke="rgba(16,185,129,.55)" stroke-width="1.2" stroke-dasharray="5 4"/>' +
      '<text x="' + (X0 + 6) + '" y="' + (toY(P.V0 * 0.632) - 6) + '" fill="#10b981" font-size="10">63.2%</text>';
    HOLO.L0(g);
    HOLO.L1(''); HOLO.L2(''); HOLO.L3('');
  };

  window.frame = function(dt, tGlobal){
    S.t = Math.min(tau() * SPAN_TAU, S.t + dt * tau());   // 1 秒 ≈ 1τ
    var x = toX(S.t), y = toY(vAt(S.t));

    HOLO.L1(
      '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="8" fill="url(#sphere-amber)" filter="url(#neon-glow)"/>' +
      '<line x1="' + x.toFixed(1) + '" y1="' + y.toFixed(1) + '" x2="' + x.toFixed(1) + '" y2="' + Y0 +
        '" stroke="rgba(245,158,11,.45)" stroke-width="1" stroke-dasharray="4 4"/>'
    );

    // 电路示意：电池 → 电阻 → 电容
    var pct = vAt(S.t) / Math.max(0.1, P.V0);
    HOLO.L2(
      '<g transform="translate(520,60)" opacity="0.9">' +
      '<rect x="0" y="0" width="120" height="58" fill="none" stroke="rgba(56,189,248,.3)"/>' +
      '<rect x="10" y="26" width="100" height="6" fill="rgba(245,158,11,.55)"/>' +
      '<rect x="10" y="26" width="' + Math.max(0, 100 * pct).toFixed(1) + '" height="6" fill="#38bdf8"/>' +
      '<text x="10" y="-6" fill="#94a3b8" font-size="9">CHARGE STORE</text>' +
      '</g>'
    );

    var lock = HOLO.highlight()
      ? '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="22" fill="none" stroke="#10b981" stroke-width="1.4" stroke-dasharray="5 4"/>'
      : '';
    HOLO.L3(lock +
      '<g transform="translate(24,24)">' +
      '<rect x="0" y="0" width="236" height="58" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="18" fill="#38bdf8" font-size="10" letter-spacing="1.2">RC TELEMETRY</text>' +
      '<text x="10" y="40" fill="#e0f2fe" font-size="12">τ = ' + tau().toFixed(1) + ' ms   Vc = ' + vAt(S.t).toFixed(2) + ' V</text>' +
      '</g>'
    );

    HOLO.metric('tau', tau().toFixed(1) + ' ms');
    HOLO.metric('t63', tau().toFixed(1) + ' ms');
    HOLO.metric('v', vAt(S.t).toFixed(2) + ' V');
    HOLO.metric('pct', (pct * 100).toFixed(1) + ' %');

    HOLO.telemetry(pct, Math.min(1, S.t / (tau() * SPAN_TAU)));
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