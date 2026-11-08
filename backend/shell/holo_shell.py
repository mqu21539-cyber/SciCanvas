# -*- coding: utf-8 -*-
"""SciCanvas 全息 2.5D 底座（Holo Shell）。

设计目标：把「四层 Z 轴、示波器、子弹时间、四滤镜、残影、靶向锁定、运镜」
这些交互做成**一次性写好的运行时**，模板作者（以及双 Agent 的 Coder 模型）
只需要填一个 `frame(dt)` 函数，约 50 行。

这个文件同时被两条路线使用：
  * 模板路径：templates/*.py 只提供 META + JS
  * 双 Agent 路径：后端把模型输出的 frame 逻辑拼进来

对外契约（模板里能用的东西）：
    HOLO.P                 当前参数对象
    HOLO.p(key)            读参数
    HOLO.L0/L1/L2/L3(html) 往四层里写内容（内容没变会自动跳过，省性能）
    HOLO.telemetry(a, b)   推两个 0~1 归一化值到示波器
    HOLO.metric(id, text)  更新右侧指标
    HOLO.reset()           请求重置（由模板实现的 reset() 响应）

模板需要提供：
    function reset() { ... }          参数变化 / 重置按钮时调用
    function frame(dt) { ... }        每帧调用，dt 已乘过时间膨胀系数

自愈契约保持不变：window.onerror → postMessage({type:'SCICANVAS_ERROR'})。
"""
from __future__ import annotations

import json

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<script>
window.onerror = function(msg, url, line, col, error) {
  try {
    window.parent.postMessage({ type: 'SCICANVAS_ERROR', message: String(msg), line: line }, '*');
  } catch (e) {}
  return false;
};
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
  :root {
    --mx: 50%; --my: 40%;
    --z-gap: 44px;
    --cyan: #38bdf8;
    --magenta: #f43f5e;
    --emerald: #10b981;
    --amber: #f59e0b;
    --ink: #030712;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    background: var(--ink);
    color: #e2e8f0;
    font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', Menlo, monospace;
    overflow: hidden;
  }
  .ws {
    position: relative; width: 100%; height: 100%;
    display: flex; flex-direction: column;
    background-image: radial-gradient(620px circle at var(--mx) var(--my), rgba(56,189,248,0.13), transparent 46%);
    transition: background-color .35s ease, filter .35s ease;
  }
  .ws::before {
    content: ''; position: absolute; inset: 0; pointer-events: none; z-index: 1;
    background-image:
      linear-gradient(to right, rgba(56,189,248,0.05) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(56,189,248,0.05) 1px, transparent 1px);
    background-size: 40px 40px;
    mask-image: radial-gradient(ellipse at 50% 40%, #000 30%, transparent 80%);
  }

  /* ---------- 多光谱滤镜 ---------- */
  .ws[data-theme="blueprint"] { background-color: #0a2540; --cyan: #ffffff; }
  .ws[data-theme="blueprint"]::before {
    background-image:
      linear-gradient(to right, rgba(255,255,255,0.16) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(255,255,255,0.16) 1px, transparent 1px);
  }
  .ws[data-theme="thermal"] { filter: hue-rotate(195deg) saturate(2.5) contrast(1.12); }
  .ws[data-theme="amber"] { background-color: #0c0800; filter: sepia(1) hue-rotate(-15deg) saturate(3) contrast(1.1); }
  .ws[data-theme="amber"]::after {
    content: ''; position: absolute; inset: 0; pointer-events: none; z-index: 80;
    background: repeating-linear-gradient(0deg, rgba(0,0,0,.26), rgba(0,0,0,.26) 1px, transparent 1px, transparent 3px);
  }

  /* ---------- 顶栏 ---------- */
  header {
    position: relative; z-index: 30; flex: none;
    display: flex; align-items: baseline; gap: 14px;
    padding: 12px 18px; border-bottom: 1px solid rgba(56,189,248,.18);
    background: rgba(2,6,23,.72); backdrop-filter: blur(8px);
  }
  header h1 { font-size: 15px; letter-spacing: .04em; color: var(--cyan); font-weight: 700; }
  header .sub { font-size: 11px; color: #64748b; }
  header .law {
    margin-left: auto; font-size: 12px; color: #86efac;
    border: 1px solid rgba(16,185,129,.3); background: rgba(16,185,129,.07);
    padding: 4px 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 46%;
  }

  /* ---------- 主体 ---------- */
  main { position: relative; z-index: 10; flex: 1; display: flex; min-height: 0; }
  aside {
    width: 256px; flex: none; padding: 12px;
    border-right: 1px solid rgba(56,189,248,.14);
    background: rgba(2,6,23,.55); overflow-y: auto;
  }
  aside::-webkit-scrollbar { width: 6px; }
  aside::-webkit-scrollbar-thumb { background: rgba(56,189,248,.25); }
  .sec-title {
    font-size: 10px; letter-spacing: .12em; color: #475569;
    margin: 6px 0 8px; display: flex; justify-content: space-between; align-items: center;
  }
  .cap { position: relative; border: 1px solid rgba(56,189,248,.18); background: rgba(2,6,23,.6); padding: 7px 9px; margin-bottom: 7px; transition: border-color .15s, box-shadow .15s; }
  .cap.on { border-color: var(--cyan); box-shadow: 0 0 14px rgba(56,189,248,.25) inset; }
  .cap .row { display: flex; justify-content: space-between; align-items: center; font-size: 11px; margin-bottom: 5px; }
  .cap .nm { color: #bae6fd; }
  .cap .vl { color: var(--cyan); background: rgba(56,189,248,.12); border: 1px solid rgba(56,189,248,.25); padding: 1px 6px; transition: transform .18s cubic-bezier(.34,1.56,.64,1); display: inline-block; }
  .cap.on .vl { transform: scale(1.08); }
  /* 机械刻度尺：视觉层是刻度 + 游标，真正的控件是盖在上面的透明 range */
  .cap .ruler { position: relative; height: 26px; display: flex; align-items: center; }
  .cap .ticks { display: flex; align-items: flex-end; justify-content: space-between; width: 100%; height: 18px; }
  .cap .tk { width: 1px; height: 6px; background: #24405a; transition: background .1s, height .1s; }
  .cap .tk.major { height: 11px; background: #2f5470; }
  .cap .tk.lit { background: var(--cyan); box-shadow: 0 0 6px rgba(56,189,248,.7); }
  .cap .needle {
    position: absolute; top: 2px; left: var(--frac, 0%); width: 2px; height: 14px;
    background: #f8fafc; box-shadow: 0 0 10px var(--cyan);
    transform: translateX(-1px); transition: left .06s linear;
  }
  .cap .needle::after {
    content: ''; position: absolute; left: -3px; top: -3px; width: 8px; height: 4px;
    background: #f8fafc; clip-path: polygon(50% 100%, 0 0, 100% 0);
  }
  input[type=range] {
    -webkit-appearance: none; appearance: none; position: absolute; inset: 0; width: 100%;
    height: 100%; margin: 0; background: transparent; outline: none; cursor: ew-resize; opacity: 0;
  }
  /* 必须锁在胶囊内部：少了 position:relative 时 inset:0 会相对页面定位，
     于是最后一根滑块盖住整页，其它几根永远点不到（真发生过）。 */
  .cap > input[type=range] { position: absolute; inset: 0; }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none; width: 18px; height: 18px; border-radius: 50%;
    background: transparent; cursor: ew-resize;
  }
  .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 4px; }
  .metric { border: 1px solid rgba(56,189,248,.15); background: rgba(2,6,23,.6); padding: 6px 8px; }
  .metric .k { font-size: 9px; color: #64748b; }
  .metric .v { font-size: 12px; color: #bae6fd; margin-top: 2px; }

  /* ---------- 舞台 ---------- */
  .stage-wrap { position: relative; flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .stage-area { position: relative; flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; perspective: 1200px; }
  .stage {
    position: relative; width: 92%; height: 88%; transform-style: preserve-3d;
    transition: transform .18s ease-out;
  }
  .layer {
    position: absolute; inset: 0; transition: transform .5s cubic-bezier(.22,1,.36,1), opacity .2s, border-color .25s, background-color .25s;
    border: 1px solid transparent; pointer-events: none;
  }
  .layer svg { width: 100%; height: 100%; overflow: visible; display: block; }
  .stage.is3d .layer { pointer-events: auto; border-color: rgba(56,189,248,.3); background: rgba(15,23,42,.22); }
  /* 声明了可抓握参数的实验：L1 实体层接受指针，光标变成抓手 */
  .stage.grabbable #l1 { pointer-events: auto; }
  .stage.grabbable #l1 * { pointer-events: none; }
  .stage.grabbable #l1 { cursor: grab; }
  .stage.grabbable.grabbing #l1 { cursor: grabbing; }
  .stage.grabbable::after {
    content: '⇕ 可在画布内直接拖动';
    position: absolute; right: 10px; bottom: 10px; z-index: 40;
    font-size: 10px; color: rgba(56,189,248,.75); letter-spacing: .08em;
    padding: 2px 7px; border: 1px solid rgba(56,189,248,.25);
    background: rgba(2,6,23,.6); pointer-events: none;
  }
  .stage.is3d .L0 { transform: translateZ(0); }
  .stage.is3d .L1 { transform: translateZ(calc(var(--z-gap) * 1)); filter: drop-shadow(-10px 16px 8px rgba(0,0,0,.6)); }
  .stage.is3d .ghostly { transform: translateZ(calc(var(--z-gap) * 1.4)); }
  .stage.is3d .L2 { transform: translateZ(calc(var(--z-gap) * 2)); }
  .stage.is3d .L3 { transform: translateZ(calc(var(--z-gap) * 3)); }

  /* 平行宇宙残影：把当前画面染成品红并半透明压在实体下面 */
  .layer.ghostly { display: none; opacity: .42; filter: hue-rotate(285deg) saturate(2.2); }
  .layer.ghostly.on { display: block; pointer-events: none; }
  .layer.ghostly svg { position: absolute; inset: 0; }
  .stage.is3d .layer:hover {
    opacity: 1; border-color: var(--cyan); background: rgba(14,165,233,.06);
  }
  .stage.is3d:hover .layer { opacity: .3; }
  .stage.is3d .layer:hover::after {
    content: attr(data-label); position: absolute; top: -22px; left: -1px;
    background: var(--cyan); color: #030712; font-size: 10px; font-weight: 700; padding: 2px 8px;
  }
  .badge {
    position: absolute; top: 8px; left: 10px; z-index: 40; font-size: 10px; color: #7dd3fc;
    background: rgba(2,6,23,.8); border: 1px solid rgba(56,189,248,.3); padding: 3px 9px;
  }
  .hud {
    position: absolute; top: 8px; right: 10px; z-index: 40; display: flex; gap: 6px;
  }
  .hud button, .dock button {
    font-family: inherit; font-size: 10px; cursor: pointer;
    background: rgba(14,165,233,.14); border: 1px solid rgba(56,189,248,.45);
    color: #e0f2fe; padding: 4px 9px; transition: .15s;
  }
  .hud button:hover, .dock button:hover, .hud button.on, .dock button.on {
    background: var(--cyan); color: #030712; font-weight: 700;
  }
  .hud button.ghost { border-color: var(--magenta); color: #fda4af; background: rgba(244,63,94,.14); }
  .hud button.ghost.on { background: var(--magenta); color: #fff; }

  /* ---------- 底部扩展坞 ---------- */
  .dock {
    flex: none; display: flex; align-items: center; gap: 10px;
    padding: 7px 12px; border-top: 1px solid rgba(56,189,248,.18);
    background: rgba(2,6,23,.8); backdrop-filter: blur(10px);
  }
  .dock .grp { display: flex; align-items: center; gap: 5px; }
  .dock .lbl { font-size: 9px; color: #475569; letter-spacing: .08em; margin-right: 2px; }
  .scope { position: relative; flex: 1; min-width: 120px; height: 46px; background: rgba(2,6,23,.9); border: 1px solid rgba(56,189,248,.22); }
  .scope canvas { display: block; width: 100%; height: 100%; }
  .scope .tag { position: absolute; top: 1px; left: 5px; font-size: 8px; color: rgba(148,163,184,.7); pointer-events: none; }
</style>
</head>
<body>
<div class="ws" id="ws" data-theme="holo">
  <header>
    <h1>__TITLE__</h1>
    <span class="sub">__SUBTITLE__</span>
    <span class="law" title="__FORMULA__">__FORMULA__</span>
  </header>

  <main>
    <aside id="panel">
      <div class="sec-title"><span>// PARAM CAPSULES</span><span id="chaosTag"></span></div>
      <div id="capsules"></div>
      <div class="sec-title" style="margin-top:14px">// TELEMETRY</div>
      <div class="metrics" id="metrics"></div>
    </aside>

    <section class="stage-wrap">
      <div class="stage-area">
        <div class="badge" id="badge">2D ORTHOGRAPHIC VIEW</div>
        <div class="hud">
          <button id="btn3d">❖ 2.5D 拆解</button>
          <button id="btnGhost" class="ghost">👻 锁定残影</button>
          <button id="btnCinema">🎬 运镜</button>
        </div>
        <div class="stage" id="stage">
          <div class="layer L0" data-label="L0 // 坐标基准"><svg id="l0" viewBox="0 0 700 400" preserveAspectRatio="xMidYMid meet"></svg></div>
          <div class="layer L1" data-label="L1 // 物理实体"><svg id="l1" viewBox="0 0 700 400" preserveAspectRatio="xMidYMid meet"></svg></div>
          <div class="layer ghostly" id="ghostLayer" data-label="L1-γ // 平行残影">
            <svg id="g1" viewBox="0 0 700 400" preserveAspectRatio="xMidYMid meet"></svg>
            <svg id="g2" viewBox="0 0 700 400" preserveAspectRatio="xMidYMid meet"></svg>
          </div>
          <div class="layer L2" data-label="L2 // 矢量与尾迹"><svg id="l2" viewBox="0 0 700 400" preserveAspectRatio="xMidYMid meet"></svg></div>
          <div class="layer L3" data-label="L3 // 遥测 HUD"><svg id="l3" viewBox="0 0 700 400" preserveAspectRatio="xMidYMid meet"></svg></div>
        </div>
      </div>

      <div class="dock">
        <div class="grp">
          <button data-speed="0">⏸ 冻结</button>
          <button data-speed="0.15">0.1x</button>
          <button data-speed="1" class="on">1.0x</button>
          <button id="btnStep">+1帧</button>
          <button id="btnMute" title="刻度棘轮音效开关">🔊</button>
        </div>
        <div class="scope">
          <span class="tag" id="scopeTag">LIVE SCOPE</span>
          <canvas id="scope" width="360" height="46"></canvas>
        </div>
        <div class="grp">
          <span class="lbl">OPTICS</span>
          <button data-theme="holo" class="on">全息</button>
          <button data-theme="blueprint">蓝图</button>
          <button data-theme="thermal">热成像</button>
          <button data-theme="amber">CRT</button>
        </div>
      </div>
    </section>
  </main>
</div>

<svg width="0" height="0" style="position:absolute"><defs>
  <radialGradient id="sphere-cyan" cx="32%" cy="30%" r="68%">
    <stop offset="0%" stop-color="#e0f2fe"/><stop offset="35%" stop-color="#38bdf8"/>
    <stop offset="80%" stop-color="#0369a1"/><stop offset="100%" stop-color="#082f49"/>
  </radialGradient>
  <radialGradient id="sphere-amber" cx="32%" cy="30%" r="68%">
    <stop offset="0%" stop-color="#fef3c7"/><stop offset="35%" stop-color="#f59e0b"/>
    <stop offset="85%" stop-color="#78350f"/><stop offset="100%" stop-color="#451a03"/>
  </radialGradient>
  <linearGradient id="block-3d" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#7dd3fc"/><stop offset="50%" stop-color="#0284c7"/><stop offset="100%" stop-color="#0c4a6e"/>
  </linearGradient>
  <filter id="neon-glow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <marker id="ar-cyan" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 1 L10 5 L0 9 z" fill="#38bdf8"/></marker>
  <marker id="ar-amber" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 1 L10 5 L0 9 z" fill="#f59e0b"/></marker>
  <marker id="ar-magenta" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 1 L10 5 L0 9 z" fill="#f43f5e"/></marker>
</defs></svg>

<script>
(function(){
  'use strict';
  var SPEC = __SPEC__;

  // ---------------- 运行时状态 ----------------
  var vals = {};
  SPEC.controls.forEach(function(c){ vals[c.id] = c.default; });

  // P 既是对象也是函数：模型经常写 HOLO.P('k')，模板里写 HOLO.P.k，
  // 两种都得能用，否则一调就 TypeError，整页直接空白（踩过）。
  var P = new Proxy(function(key){ return vals[key]; }, {
    get: function(t, k){
      if (k === 'toJSON') return function(){ return vals; };
      return vals[k];
    },
    set: function(t, k, v){ vals[k] = v; return true; },
    has: function(t, k){ return k in vals; },
    ownKeys: function(){ return Object.keys(vals); },
    getOwnPropertyDescriptor: function(t, k){
      return { value: vals[k], enumerable: true, configurable: true, writable: true };
    }
  });

  var svg = {
    l0: document.getElementById('l0'),
    l1: document.getElementById('l1'),
    l2: document.getElementById('l2'),
    l3: document.getElementById('l3')
  };
  var last = { l0: null, l1: null, l2: null, l3: null };

  // 内容没变就不重写 DOM：L0 往往几帧才变一次，省下来的都是帧率
  function layer(name, html) {
    html = String(html);
    if (last[name] === html) return;
    last[name] = html;
    svg[name].innerHTML = html;
  }

  var TIME_SCALE = 1, STEP_ONCE = false, HIGHLIGHT = null, RULERS = {}, GRAB = null, METRIC = {};
  // 每个参数一个重绘函数：外部改值（混沌注入/画布拖拽）后调它同步刻度尺
  // GRAB：当前被声明为「可在画布里抓握」的参数，模板通过 HOLO.bindDrag(key) 注册

  // ---------------- 棘轮音效 ----------------
  // 关键是**复用同一个 AudioContext**：文档里那个每次点击 new 一个的写法，
  // 点到第 6 下就没声了（浏览器对 AudioContext 数量有上限）。
  var AC = null, MUTED = false;
  function getAC() {
    if (MUTED) return null;
    try {
      if (!AC) AC = new (window.AudioContext || window.webkitAudioContext)();
      if (AC.state === 'suspended') AC.resume();
      return AC;
    } catch (e) { return null; }
  }
  function click(freq, dur, gain) {
    var ac = getAC();
    if (!ac) return;
    var t = ac.currentTime;
    var o = ac.createOscillator(), g = ac.createGain();
    o.type = 'square';
    o.frequency.setValueAtTime(freq, t);
    g.gain.setValueAtTime(gain, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(ac.destination);
    o.start(t); o.stop(t + dur);
  }
  function ratchet() { click(1480, 0.022, 0.045); }

  function postToParent(msg) {
    try { if (window.parent && window.parent !== window) window.parent.postMessage(msg, '*'); } catch (e) {}
  }


  // ---------------- 示波器 ----------------
  var scope = document.getElementById('scope');
  var sctx = scope.getContext('2d');
  var N = 120, ch1 = new Array(N).fill(0.5), ch2 = new Array(N).fill(0.5), hasCh2 = false;

  function drawScope() {
    var w = scope.width, h = scope.height;
    sctx.clearRect(0, 0, w, h);
    sctx.strokeStyle = 'rgba(56,189,248,.08)';
    sctx.lineWidth = 1;
    for (var x = 0; x < w; x += 30) { sctx.beginPath(); sctx.moveTo(x, 0); sctx.lineTo(x, h); sctx.stroke(); }
    function wave(arr, color, dash) {
      sctx.beginPath(); sctx.strokeStyle = color; sctx.lineWidth = 1.4; sctx.setLineDash(dash || []);
      for (var i = 0; i < arr.length; i++) {
        var px = (i / (arr.length - 1)) * w;
        var py = h - 3 - arr[i] * (h - 6);
        i === 0 ? sctx.moveTo(px, py) : sctx.lineTo(px, py);
      }
      sctx.stroke(); sctx.setLineDash([]);
    }
    if (hasCh2) wave(ch2, 'rgba(244,63,94,.75)', [4, 3]);
    wave(ch1, '#38bdf8');
  }

  // ---------------- 对外 API ----------------
  var api = {
    P: P,
    p: function(k){ return vals[k]; },
    L0: function(h){ layer('l0', h); },
    L1: function(h){ layer('l1', h); },
    L2: function(h){ layer('l2', h); },
    L3: function(h){ layer('l3', h); },
    telemetry: function(a, b) {
      ch1.push(Math.max(0, Math.min(1, a))); ch1.shift();
      if (b === undefined) hasCh2 = false;
      else { ch2.push(Math.max(0, Math.min(1, b))); ch2.shift(); hasCh2 = true; }
      drawScope();
    },
    metric: function(id, text) {
      var el = document.getElementById('m_' + id);
      if (!el) return;
      // 数字滚动：把「49.5 m」拆成数字+尾巴，每帧缓动逼近目标值，
      // 直接每帧写 textContent 会闪，直接跳变又生硬。
      var m = String(text).match(/^(-?\d+(?:\.(\d+))?)([\s\S]*)$/);
      if (!m) { el.textContent = text; METRIC[id] = null; return; }
      var st = METRIC[id];
      if (!st) {
        METRIC[id] = { cur: parseFloat(m[1]), tgt: parseFloat(m[1]), dec: (m[2] || '').length, tail: m[3], el: el };
        el.textContent = text;
        return;
      }
      st.tgt = parseFloat(m[1]);
      st.dec = (m[2] || '').length;
      st.tail = m[3];
    },
    iso: function(x, y, z, ox, oy) {
      var rad = Math.PI / 6, OX = (ox === undefined ? 350 : ox), OY = (oy === undefined ? 240 : oy);
      return { u: OX + (x - y) * Math.cos(rad), v: OY + (x + y) * Math.sin(rad) - (z || 0) };
    },
    highlight: function(){ return HIGHLIGHT; },
    // 外部/画布内改参数：统一走这里，刻度尺与父窗口才会跟着动
    setP: function(key, value){
      P[key] = value;
      if (RULERS[key]) RULERS[key]();
      api.reset();
      postToParent({ type: 'SYNC_FROM_CANVAS', key: key, value: value });
    },
    // 直接抓握：模板只要声明「哪个参数可以抓」，底座负责手势与同步
    bindDrag: function(key){
      var ctrl = null;
      SPEC.controls.forEach(function(c){ if (c.id === key) ctrl = c; });
      if (!ctrl) return false;
      GRAB = { key: key, ctrl: ctrl };
      stage.classList.add('grabbable');
      return true;
    },
    ghostActive: function(){ return !!ghostHTML; },
    timeScale: function(){ return TIME_SCALE; }
  };
  window.HOLO = api;

  // ---------------- 参数胶囊（机械刻度尺） ----------------
  // 视觉上换成游标卡尺式的刻度盘，但**底下仍然是原生 input[type=range]**：
  // 它只被设成透明盖在上面，所以已有的选择器、input 事件、外部脚本全部照旧。
  var capBox = document.getElementById('capsules');
  var TICKS = 28;

  function syncRuler(wrap, input, c) {
    var frac = (parseFloat(input.value) - c.min) / ((c.max - c.min) || 1);
    frac = Math.max(0, Math.min(1, frac));
    wrap.style.setProperty('--frac', (frac * 100).toFixed(2) + '%');
    var ticks = wrap.querySelectorAll('.tk');
    var lit = Math.round(frac * (ticks.length - 1));
    for (var i = 0; i < ticks.length; i++) {
      ticks[i].className = 'tk' + (i <= lit ? ' lit' : '') + (i % 4 === 0 ? ' major' : '');
    }
    // 每跨过一格响一下（不是每像素都响），听起来才像棘轮
    if (wrap._lit !== undefined && wrap._lit !== lit) ratchet();
    wrap._lit = lit;
  }

  SPEC.controls.forEach(function(c){
    var wrap = document.createElement('div');
    wrap.className = 'cap';
    var ticksHtml = '';
    for (var i = 0; i < TICKS; i++) ticksHtml += '<i class="tk' + (i % 4 === 0 ? ' major' : '') + '"></i>';
    wrap.innerHTML =
      '<div class="row"><span class="nm">' + c.id + ' <b>' + c.label + '</b></span>' +
      '<span class="vl" id="v_' + c.id + '">' + P[c.id] + (c.unit || '') + '</span></div>' +
      '<div class="ruler"><div class="ticks">' + ticksHtml + '</div><div class="needle"></div></div>';
    var input = document.createElement('input');
    input.type = 'range'; input.min = c.min; input.max = c.max; input.step = c.step; input.value = P[c.id];
    input.setAttribute('data-k', c.id);
    input.addEventListener('input', function(){
      var val = parseFloat(input.value);
      P[c.id] = val;
      document.getElementById('v_' + c.id).textContent = val + (c.unit || '');
      syncRuler(wrap, input, c);
      api.reset();
    });
    input.addEventListener('pointerenter', function(){
      wrap.classList.add('on');
      HIGHLIGHT = c.id;
    });
    input.addEventListener('pointerleave', function(){
      wrap.classList.remove('on');
      HIGHLIGHT = null;
    });
    wrap.appendChild(input);
    capBox.appendChild(wrap);
    syncRuler(wrap, input, c);
    RULERS[c.id] = function(){
      input.value = String(P[c.id]);
      document.getElementById('v_' + c.id).textContent = P[c.id] + (c.unit || '');
      syncRuler(wrap, input, c);
    };
  });

  // ---------------- 指标 ----------------
  var metBox = document.getElementById('metrics');
  SPEC.metrics.forEach(function(m){
    var d = document.createElement('div');
    d.className = 'metric';
    d.innerHTML = '<div class="k">' + m.label + '</div><div class="v" id="m_' + m.id + '">—</div>';
    metBox.appendChild(d);
  });

  // ---------------- 视差 / 2.5D / 残影 / 运镜 ----------------
  var ws = document.getElementById('ws');
  var stage = document.getElementById('stage');
  var badge = document.getElementById('badge');
  var is3D = false, rotX = 56, rotZ = -30, zGap = 44, dragging = false, cinema = null;
  var ghostHTML = { l1: null, l2: null };

  // ---------------- 画布内直接抓握 ----------------
  // 模板在 reset() 里调 HOLO.bindDrag('ang')，底座就把 L1 层变成可拖的：
  // 上/下拖动 → 线性映射到该参数的 [min, max]，边走边重置，并把新值回传父窗口。
  (function initGrab() {
    var l1 = document.getElementById('l1');
    if (!l1) return;

    function apply(e) {
      if (!GRAB || is3D) return;
      var r = document.querySelector('.stage-area').getBoundingClientRect();
      var frac = 1 - (e.clientY - r.top) / (r.height || 1);   // 往上拖 = 增大
      frac = Math.max(0, Math.min(1, frac));
      var c = GRAB.ctrl, step = c.step || 0.01;
      var v = c.min + frac * (c.max - c.min);
      v = Math.round(v / step) * step;
      v = Math.max(c.min, Math.min(c.max, v));
      v = Math.round(v * 1000) / 1000;
      api.setP(GRAB.key, v);       // reset + 刻度尺 + 回传父窗口
    }

    l1.addEventListener('pointerdown', function (e) {
      if (!GRAB || is3D) return;
      e.preventDefault();
      stage.classList.add('grabbing');
      try { l1.setPointerCapture(e.pointerId); } catch (e2) {}
      apply(e);
    });
    l1.addEventListener('pointermove', function (e) {
      if (!GRAB || is3D || !e.buttons) return;
      apply(e);
    });
    ['pointerup', 'pointercancel'].forEach(function (t) {
      l1.addEventListener(t, function (e) {
        stage.classList.remove('grabbing');
        try { l1.releasePointerCapture(e.pointerId); } catch (e2) {}
      });
    });
  })();

  function applyStage() {
    stage.style.transform = is3D
      ? 'rotateX(' + rotX + 'deg) rotateZ(' + rotZ + 'deg) scale(.84)'
      : 'none';
    badge.textContent = is3D
      ? '2.5D EXPLODED // X' + Math.round(rotX) + '° Z' + Math.round(rotZ) + '° GAP' + Math.round(zGap)
      : '2D ORTHOGRAPHIC VIEW';
  }

  document.getElementById('btn3d').addEventListener('click', function(){
    is3D = !is3D;
    this.classList.toggle('on', is3D);
    this.textContent = is3D ? '❖ 复位 2D' : '❖ 2.5D 拆解';
    stage.classList.toggle('is3d', is3D);
    applyStage();
  });

  document.getElementById('btnGhost').addEventListener('click', function(){
    var box = document.getElementById('ghostLayer');
    if (ghostHTML.l1 !== null) {
      ghostHTML = { l1: null, l2: null };
      box.classList.remove('on');
      this.classList.remove('on');
      this.textContent = '👻 锁定残影';
    } else {
      // 把当前 L1/L2 的画面冻结成一层品红虚影，之后实体会继续动，残影留在原地
      ghostHTML = { l1: svg.l1.innerHTML, l2: svg.l2.innerHTML };
      document.getElementById('g1').innerHTML = ghostHTML.l1;
      document.getElementById('g2').innerHTML = ghostHTML.l2;
      box.classList.add('on');
      this.classList.add('on');
      this.textContent = '👻 清除残影';
    }
  });

  document.getElementById('btnCinema').addEventListener('click', function(){
    if (cinema) { clearInterval(cinema); cinema = null; this.classList.remove('on'); return; }
    if (!is3D) document.getElementById('btn3d').click();
    this.classList.add('on');
    var t = 0, self = this;
    cinema = setInterval(function(){
      t += 0.03;
      rotZ = -30 + Math.sin(t) * 26;
      rotX = 54 + Math.cos(t * 0.8) * 10;
      zGap = 44 + Math.sin(t * 1.5) * 18;
      ws.style.setProperty('--z-gap', zGap + 'px');
      applyStage();
      if (t > 40) { clearInterval(cinema); cinema = null; self.classList.remove('on'); }
    }, 16);
  });

  ws.addEventListener('pointermove', function(e){
    var r = ws.getBoundingClientRect();
    ws.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    ws.style.setProperty('--my', (e.clientY - r.top) + 'px');
    if (is3D && dragging) {
      rotZ = Math.max(-70, Math.min(70, rotZ + e.movementX * 0.35));
      rotX = Math.max(22, Math.min(74, rotX - e.movementY * 0.35));
      applyStage();
    }
  });
  ws.addEventListener('pointerdown', function(e){
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
    dragging = true;
  });
  window.addEventListener('pointerup', function(){ dragging = false; });
  ws.addEventListener('wheel', function(e){
    if (!is3D) return;
    e.preventDefault();
    zGap = Math.max(16, Math.min(100, zGap - e.deltaY * 0.06));
    ws.style.setProperty('--z-gap', zGap + 'px');
    applyStage();
  }, { passive: false });

  // ---------------- 时间膨胀 ----------------
  document.querySelectorAll('.dock button[data-speed]').forEach(function(btn){
    btn.addEventListener('click', function(){
      TIME_SCALE = parseFloat(btn.dataset.speed);
      document.querySelectorAll('.dock button[data-speed]').forEach(function(b){ b.classList.remove('on'); });
      btn.classList.add('on');
    });
  });
  document.getElementById('btnStep').addEventListener('click', function(){
    TIME_SCALE = 0; STEP_ONCE = true;
  });
  var muteBtn = document.getElementById('btnMute');
  if (muteBtn) {
    muteBtn.addEventListener('click', function(){
      MUTED = !MUTED;
      muteBtn.textContent = MUTED ? '🔇' : '🔊';
      muteBtn.classList.toggle('on', !MUTED);
      if (!MUTED) ratchet();
    });
  }

  // ---------------- 滤镜 ----------------
  document.querySelectorAll('.dock button[data-theme]').forEach(function(btn){
    btn.addEventListener('click', function(){
      ws.setAttribute('data-theme', btn.dataset.theme);
      document.querySelectorAll('.dock button[data-theme]').forEach(function(b){ b.classList.remove('on'); });
      btn.classList.add('on');
    });
  });

  // ---------------- 宿主通信 ----------------
  window.addEventListener('message', function(ev){
    var d = ev.data || {};
    if (d.type === 'UPDATE_PARAM' && d.key in P) {
      P[d.key] = d.value;
      if (RULERS[d.key]) RULERS[d.key]();
      api.reset();
    } else if (d.type === 'HIGHLIGHT_TARGET') {
      HIGHLIGHT = d.active ? d.key : null;
    } else if (d.type === 'RESET') {
      api.reset();
    } else if (d.type === 'CHAOS') {
      // 混沌注入：阻尼/摩擦类参数推到 0，其余推到最大，制造极端现象
      var damping = ['mu', 'c', 'b', 'k', 'damping', 'friction', 'drag'];
      SPEC.controls.forEach(function(c){
        var low = String(c.id).toLowerCase();
        var isDamping = damping.some(function(k){ return low === k || low.indexOf(k) === 0; });
        P[c.id] = isDamping ? c.min : c.max;
        var el = document.getElementById('v_' + c.id);
        if (el) el.textContent = P[c.id] + (c.unit || '');
        var input = document.querySelector('#capsules input[data-k="' + c.id + '"]');
        if (input) input.value = P[c.id];
      });
      api.reset();
    } else if (d.type === 'GHOST_TOGGLE') {
      document.getElementById('btnGhost').click();
    }
  });

  // ---------------- 主循环 ----------------
  var T = 0, prev = performance.now(), started = false, errCount = 0;
  function loop(now) {
    // 底座脚本先于模板脚本执行，所以首帧之前模板的 reset() 还不存在——
    // 推迟到第一次循环再初始化，否则 L0 基准层会是空的。
    // 注意：首帧时模板脚本可能还没执行完（reset 还不存在），所以只在 reset
    // 真的出现之后才置 started，否则会漏掉整个初始化——顺带漏掉 bindDrag 注册。
    if (!started && typeof window.reset === 'function') { started = true; safeReset(); }
    var raw = Math.min(0.05, (now - prev) / 1000);
    prev = now;
    var dt = raw * TIME_SCALE;
    if (STEP_ONCE) { dt = 1 / 60; STEP_ONCE = false; }
    T += dt;
    // 遥测数字滚动：必须放在 dt 之后——放在前面会拿到上一帧的 undefined，
    // 首帧直接把 cur 算成 NaN，指标卡全变 "NaN"。
    for (var mk in METRIC) {
      var ms = METRIC[mk];
      if (!ms) continue;
      var d = ms.tgt - ms.cur;
      if (Math.abs(d) < 1e-4) {
        if (ms.cur !== ms.tgt) {
          ms.cur = ms.tgt;
          ms.el.textContent = ms.cur.toFixed(ms.dec) + ms.tail;
        }
        continue;
      }
      ms.cur += d * Math.min(1, dt * 16);
      ms.el.textContent = ms.cur.toFixed(ms.dec) + ms.tail;
    }
    try {
      if (typeof window.frame === 'function') window.frame(dt, T);
      errCount = 0;                       // 跑通就清零，偶发错误不会累计
    } catch (e) {
      // 关键：不要因为一次异常就把整个循环停掉。
      // 停了之后自愈接手也只是换一份 HTML，画面在换之前永远是死的（踩过）。
      errCount++;
      if (errCount <= 3) {
        try { window.onerror(String(e && e.message || e), '', 0, 0, e); } catch (e2) {}
        showFault(String(e && e.message || e));
      }
    }
    requestAnimationFrame(loop);
  }

  // 出错时在舞台中央留一行提示，总比"看起来什么都没发生"强
  var faultEl = null;
  function showFault(msg) {
    if (!faultEl) {
      faultEl = document.createElement('div');
      faultEl.style.cssText =
        'position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);z-index:60;' +
        'max-width:70%;padding:10px 14px;border:1px solid rgba(244,63,94,.5);' +
        'background:rgba(2,6,23,.9);color:#fda4af;font:12px/1.6 ui-monospace,monospace;' +
        'white-space:pre-wrap;word-break:break-all;';
      document.querySelector('.stage-area').appendChild(faultEl);
    }
    faultEl.textContent = '⚠ 实验代码抛错（自愈已触发）\n' + msg;
  }
  function clearFault() {
    if (faultEl) { faultEl.remove(); faultEl = null; }
  }

  function safeReset() {
    clearFault();
    if (typeof window.reset === 'function') {
      try { window.reset(); } catch (e) {
        showFault(String(e && e.message || e));
        try { window.onerror(String(e && e.message || e), '', 0, 0, e); } catch (e2) {}
      }
    }
  }

  api.reset = safeReset;

  // 先跑一次 reset 让模板把初始画面画出来（真正的首次调用在 loop 里）
  drawScope();
  applyStage();
  requestAnimationFrame(loop);
})();
</script>
<script>
__LAB_JS__
</script>
</body>
</html>
"""


def render(spec: dict, lab_js: str) -> str:
    """把「实验规格 + 模板 JS」拼成一份完整的单文件 HTML。

    spec: {title, subtitle, formula, controls[], metrics[]}
    lab_js: 模板提供的 JS，需定义 reset() 与 frame(dt, t)
    """
    payload = {
        "controls": [
            {
                "id": c["id"],
                "label": c.get("label", c["id"]),
                "unit": c.get("unit", ""),
                "min": c.get("min", 0),
                "max": c.get("max", 1),
                "step": c.get("step", 0.01),
                "default": c.get("default", c.get("min", 0)),
            }
            for c in spec.get("controls", [])
        ],
        "metrics": [
            {"id": m["id"], "label": m.get("label", m["id"])} for m in spec.get("metrics", [])
        ],
    }
    return (
        _TEMPLATE.replace("__TITLE__", _esc(spec.get("title", "SciCanvas Lab")))
        .replace("__SUBTITLE__", _esc(spec.get("subtitle", "")))
        .replace("__FORMULA__", _esc(spec.get("formula", "")))
        .replace("__SPEC__", json.dumps(payload, ensure_ascii=False))
        .replace("__LAB_JS__", lab_js)
    )


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )