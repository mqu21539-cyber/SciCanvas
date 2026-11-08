# -*- coding: utf-8 -*-
"""模板：双点电荷电场线（全息 2.5D 版）。"""
from shell import holo_shell

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
        {"id": "force", "label": "相互作用"},
        {"id": "F", "label": "库仑力 |F|"},
        {"id": "E0", "label": "中点场强"},
        {"id": "null", "label": "零场点"},
    ],
}

_JS = r"""
(function(){
  'use strict';
  var P = HOLO.P;
  var CX = 350, CY = 200, SCALE = 42;
  var S = { pulse: 0, lines: '', chg: '' };

  function pos(){
    var half = P.d / 2;
    return { ax: CX - half * SCALE, bx: CX + half * SCALE };
  }

  // 从每个电荷沿 N 个方向积分出电场线（准静态，reset 时算一次就够）
  function buildField(){
    var p = pos(), out = '';
    var charges = [{ x: p.ax, q: P.q1 }, { x: p.bx, q: P.q2 }];
    var DIRS = 12, STEPS = 26, H = 6;

    charges.forEach(function(c){
      if (Math.abs(c.q) < 0.1) return;
      for (var a = 0; a < DIRS; a++) {
        var ang = (a / DIRS) * Math.PI * 2;
        var x = c.x + Math.cos(ang) * 18;
        var y = CY + Math.sin(ang) * 18;
        var pts = [x.toFixed(1) + ',' + y.toFixed(1)];
        for (var s = 0; s < STEPS; s++) {
          var ex = 0, ey = 0;
          charges.forEach(function(o){
            var dx = x - o.x, dy = y - CY;
            var r2 = dx * dx + dy * dy;
            if (r2 < 64) return;
            var r = Math.sqrt(r2);
            var mag = o.q * 900 / (r2 * r);
            ex += mag * dx; ey += mag * dy;
          });
          var m = Math.hypot(ex, ey);
          if (m < 1e-6) break;
          x += (ex / m) * H; y += (ey / m) * H;
          if (x < 10 || x > 690 || y < 10 || y > 390) break;
          pts.push(x.toFixed(1) + ',' + y.toFixed(1));
        }
        if (pts.length > 3) {
          out += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="rgba(56,189,248,.34)" stroke-width="1.2"/>';
        }
      }
    });
    return out;
  }

  function chargeLayer(){
    var p = pos();
    function ball(x, q){
      var r = 10 + Math.min(14, Math.abs(q) * 2.6);
      var fill = q >= 0 ? 'url(#sphere-amber)' : 'url(#sphere-cyan)';
      var sign = q >= 0 ? '+' : '−';
      return '<circle cx="' + x.toFixed(1) + '" cy="' + CY + '" r="' + r.toFixed(1) + '" fill="' + fill +
        '" filter="url(#neon-glow)"/>' +
        '<text x="' + (x - 5).toFixed(1) + '" y="' + (CY + 6) + '" fill="#0b1220" font-size="15" font-weight="bold">' + sign + '</text>';
    }
    return ball(p.ax, P.q1) + ball(p.bx, P.q2) +
      '<line x1="' + (p.ax - 60) + '" y1="' + CY + '" x2="' + (p.bx + 60) + '" y2="' + CY +
        '" stroke="rgba(148,163,184,.22)" stroke-width="1" stroke-dasharray="4 5"/>';
  }

  window.reset = function(){
    // 直接抓握：在画布里上下拖动，等于拖动「d」滑块
    if (HOLO.bindDrag) HOLO.bindDrag('d');
    var p = pos();
    var g = '';
    for (var x = 50; x < 700; x += 50) g += '<line x1="' + x + '" y1="0" x2="' + x + '" y2="400" stroke="rgba(56,189,248,.05)"/>';
    for (var y = 0; y < 400; y += 50) g += '<line x1="0" y1="' + y + '" x2="700" y2="' + y + '" stroke="rgba(56,189,248,.05)"/>';
    g += '<text x="' + ((p.ax + p.bx) / 2 - 26).toFixed(0) + '" y="' + (CY + 42) +
      '" fill="rgba(148,163,184,.7)" font-size="11">d = ' + P.d.toFixed(1) + ' m</text>';
    HOLO.L0(g);

    S.lines = buildField();
    S.chg = chargeLayer();
    HOLO.L1(S.chg);
    HOLO.L2(S.lines);
    HOLO.L3('');
  };

  window.frame = function(dt, t){
    S.pulse += dt;
    // 电荷本身是静态的，只有靶向准星和示波器在动
    var p = pos();
    var lock = HOLO.highlight()
      ? '<circle cx="' + p.ax.toFixed(1) + '" cy="' + CY + '" r="30" fill="none" stroke="#10b981" stroke-width="1.4" stroke-dasharray="6 4"/>' +
        '<circle cx="' + p.bx.toFixed(1) + '" cy="' + CY + '" r="30" fill="none" stroke="#10b981" stroke-width="1.4" stroke-dasharray="6 4"/>'
      : '';
    HOLO.L3(lock +
      '<g transform="translate(400,24)">' +
      '<rect x="0" y="0" width="266" height="76" fill="rgba(2,6,23,.72)" stroke="rgba(56,189,248,.35)"/>' +
      '<text x="10" y="18" fill="#38bdf8" font-size="10" letter-spacing="1.2">COULOMB TELEMETRY</text>' +
      '<text x="10" y="40" fill="#e0f2fe" font-size="12">q₁=' + P.q1.toFixed(1) + '  q₂=' + P.q2.toFixed(1) + '  nC</text>' +
      '<text x="10" y="60" fill="#86efac" font-size="12">合力方向：' + (P.q1 * P.q2 >= 0 ? '相斥' : '相吸') + '</text>' +
      '</g>'
    );

    var F = 8.99 * Math.abs(P.q1 * P.q2) / (P.d * P.d);   // nC·nC/m² → 相对量
    var midE = 8.99 * (P.q1 - P.q2) / Math.pow(P.d / 2, 2);
    var nullPt = '—';
    if (P.q1 * P.q2 > 0 && Math.abs(P.q1 - P.q2) > 0.01) {
      var ratio = Math.sqrt(Math.abs(P.q1 / P.q2));
      var xr = P.d * ratio / Math.abs(1 - ratio);
      nullPt = (P.q1 * P.q2 > 0 && ratio !== 1) ? xr.toFixed(1) + ' m 外侧' : '—';
    } else if (P.q1 + P.q2 !== 0) {
      nullPt = '无（异号）';
    }
    HOLO.metric('force', P.q1 * P.q2 >= 0 ? '相斥' : '相吸');
    HOLO.metric('F', F.toFixed(2));
    HOLO.metric('E0', Math.abs(midE).toFixed(1));
    HOLO.metric('null', nullPt);

    HOLO.telemetry(Math.min(1, F / 40), Math.min(1, Math.abs(midE) / 40));
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