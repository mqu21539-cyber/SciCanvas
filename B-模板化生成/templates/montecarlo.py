# -*- coding: utf-8 -*-
"""模板：蒙特卡洛估算 π（全息 2.5D 版）。"""
import holo_shell

META = {
    "name": "montecarlo",
    "title": "蒙特卡洛：随机撒点凭什么是 π 的 3.14 倍",
    "category": "概率 / 数值方法",
    "formula": "π ≈ 4 × (落在圆内的点数 / 总点数)",
    "controls": [
        {"id": "rate", "label": "每秒撒点", "unit": "个/s", "min": 200, "max": 20000, "step": 200, "default": 4000},
        {"id": "dotsize", "label": "点大小", "unit": "px", "min": 0.5, "max": 3, "step": 0.1, "default": 1.2},
        {"id": "quadrant", "label": "象限（1=四分之一圆）", "unit": "个", "min": 1, "max": 4, "step": 1, "default": 1},
    ],
    "metrics": [
        {"id": "n", "label": "总点数"},
        {"id": "pi", "label": "π 估计"},
        {"id": "err", "label": "相对误差"},
        {"id": "ci", "label": "95% 置信半宽"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var CX = 70, CY = 320, SIDE = 250;      // 正方形左下角在 (CX, CY)
  var SHOW = 420;                          // 画面只留最近 420 个点，统计用全量
  var S = { n: 0, hit: 0, pts: [], acc: 0 };

  function px(u){ return CX + u * SIDE; }
  function py(v){ return CY - v * SIDE; }

  window.reset = function(){
    S.n = 0; S.hit = 0; S.pts = []; S.acc = 0;
    var g = '<rect x="' + CX + '" y="' + (CY - SIDE) + '" width="' + SIDE + '" height="' + SIDE +
      '" fill="none" stroke="rgba(148,163,184,.5)" stroke-width="1.4"/>';
    // 四分之一圆
    var arc = [];
    for (var i = 0; i <= 90; i++) {
      var a = (i / 90) * Math.PI / 2;
      arc.push(px(Math.cos(a)).toFixed(1) + ',' + py(Math.sin(a)).toFixed(1));
    }
    g += '<polyline points="' + arc.join(' ') + '" fill="none" stroke="rgba(56,189,248,.8)" stroke-width="1.8" filter="url(#neon-glow)"/>';
    g += '<text x="' + (CX + SIDE + 12) + '" y="' + (CY - SIDE) + '" fill="rgba(148,163,184,.7)" font-size="10">1×1</text>';
    HOLO.L0(g);
    HOLO.L1(''); HOLO.L2(''); HOLO.L3('');
  };

  window.frame = function(dt, tGlobal){
    if (dt > 0) {
      S.acc += dt * P.rate;
      var batch = Math.floor(S.acc);
      if (batch > 0) {
        S.acc -= batch;
        for (var i = 0; i < batch; i++) {
          var u = Math.random(), v = Math.random();
          var inside = (u * u + v * v) <= 1;
          if (inside) S.hit++;
          S.n++;
          S.pts.push(u, v, inside ? 1 : 0);
        }
        var maxFloats = SHOW * 3;
        if (S.pts.length > maxFloats) S.pts.splice(0, S.pts.length - maxFloats);
      }
    }

    // 点云：用一条 path 画，比几百个 circle 轻得多
    var d = '';
    for (var i = 0; i < S.pts.length; i += 3) {
      var u = S.pts[i], v = S.pts[i + 1], ins = S.pts[i + 2];
      d += 'M' + px(u).toFixed(1) + ' ' + py(v).toFixed(1) + 'h' + P.dotsize + 'v' + P.dotsize + 'h-' + P.dotsize + 'z';
    }
    HOLO.L1('<path d="' + d + '" fill="rgba(56,189,248,.55)"/>');

    var pi = S.n ? 4 * S.hit / S.n : 0;
    var se = S.n ? Math.sqrt(pi * (4 - pi) / S.n) : 0;
    var lock = HOLO.highlight()
      ? '<rect x="' + CX + '" y="' + (CY - SIDE) + '" width="' + SIDE + '" height="' + SIDE +
        '" fill="none" stroke="#10b981" stroke-dasharray="6 5"/>'
      : '';
    HOLO.L3(lock +
      '<g transform="translate(400,24)">' +
      '<rect x="0" y="0" width="266" height="76" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="18" fill="#38bdf8" font-size="10" letter-spacing="1.2">MONTE CARLO</text>' +
      '<text x="10" y="42" fill="#86efac" font-size="16">π ≈ ' + (S.n ? pi.toFixed(4) : '—') + '</text>' +
      '<text x="10" y="62" fill="rgba(148,163,184,.8)" font-size="11">N = ' + S.n + '</text>' +
      '</g>'
    );

    HOLO.metric('n', S.n.toLocaleString('en-US'));
    HOLO.metric('pi', S.n ? pi.toFixed(5) : '—');
    HOLO.metric('err', S.n ? (((pi - Math.PI) / Math.PI) * 100).toFixed(3) + ' %' : '—');
    HOLO.metric('ci', S.n ? '± ' + (1.96 * se).toFixed(5) : '—');

    HOLO.telemetry(S.n ? S.hit / S.n : 0, S.n ? Math.min(1, (pi - 3) / 0.4) : 0);
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