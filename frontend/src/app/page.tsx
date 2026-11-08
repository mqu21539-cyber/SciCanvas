"use client";
import React, { useCallback, useEffect, useRef, useState } from "react";
import katex from "katex";
import HoloCockpit, { type AgentStatus } from "../components/HoloCockpit";
import MagneticHoloButton from "../components/MagneticHoloButton";
import MathFormula, { toLatex } from "../components/MathFormula";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8010";

interface LabControl {
  id: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  description?: string;
}

interface LabPlan {
  title: string;
  subtitle: string;
  formula_latex: string;
  intuition_challenge?: string;
  controls?: LabControl[];
  visual_spec?: Record<string, string>;
}
const PRESETS = [
  {
    label: "🌊 多普勒效应与音爆临界波前",
    prompt: "演示多普勒效应（Doppler Effect）与马赫锥音爆现象：一个移动的声源周期性向外发射圆形声波波前，提供控制声源移动速度（从0到1.5倍声速）、发射频率和波速的滑块，实时显示迎面波长压缩与背后波长拉长。"
  },
  {
    label: "🏔️ 梯度下降与动量逃逸局部最优",
    prompt: "可视化机器学习中的梯度下降（Gradient Descent with Momentum）：绘制一条带有局部极小值坑和全局最小值谷的复杂非凸损失函数曲线，一个小球从山顶滚下，提供学习率（Learning Rate）、动量系数（Momentum）和初始位置滑块，展示小球如何靠动量冲出局部最优。"
  },
  {
    label: "🌌 双星引力弹弓与混沌三体轨道",
    prompt: "模拟双星系统与探测器引力弹弓效应：两颗大质量恒星相互绕转，发射一颗轻质探测器穿越引力场，提供恒星质量比、探测器发射初速度和发射角度滑块，绘制彩色尾迹并实时显示探测器动能变化曲线。"
  }
];
export default function SciCanvasApp() {
  const [prompt, setPrompt] = useState(PRESETS[0].prompt);
  const [loading, setLoading] = useState(false);
  const [fixing, setFixing] = useState(false);
  const [plan, setPlan] = useState<LabPlan | null>(null);
  const [htmlCode, setHtmlCode] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [elapsed, setElapsed] = useState(0);
  // 后端路由结果：走模板（快）还是双 Agent（慢），用于顶部徽标
  const [engine, setEngine] = useState<
    { mode: "template" | "agent"; template?: string | null; ms: number; cached?: boolean } | null
  >(null);
  // 如果输入里带 arXiv 编号，后端会抓摘要，这里存一下用于展示出处
  const [paper, setPaper] = useState<{ id: string; title: string; url: string } | null>(null);
  // 全息座舱：双 Agent 脉冲条与自愈计数
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("IDLE");
  const [healCount, setHealCount] = useState(0);
  // 画布内直接抓握后，宿主收到的参数回传（短暂提示）
  const [canvasSync, setCanvasSync] = useState<{ key: string; value: number } | null>(null);
  const [viewMode, setViewMode] = useState<"preview" | "code">("preview");
  // 「先猜后试」：用户先选一个预测，再去拖滑块验证
  const [guess, setGuess] = useState<string | null>(null);
  // 「双沙盒同屏对比」：两块独立 iframe 跑同一份代码，各自拖滑块
  const [split, setSplit] = useState(false);
  const [splitNonce, setSplitNonce] = useState(0);
  // 当前请求的控制器：新一轮生成会取消上一轮，避免两个结果互相覆盖
  const abortRef = useRef<AbortController | null>(null);
  const [restored, setRestored] = useState(false);
  // SSE 阶段：真实进度，不再是按秒数猜
  const [stage, setStage] = useState<string>("");
  const [progress, setProgress] = useState(0);

  const applyStage = (payload: { stage: string; template?: string; cached?: boolean }) => {
    switch (payload.stage) {
      case "routing":
        setStage("① 正在分诊：这个概念能用模板表达吗…");
        setProgress(8);
        break;
      case "routed":
        if (payload.template) {
          setStage(`✓ 命中模板 ${payload.template}，正在渲染…`);
          setProgress(55);
        } else {
          setStage("→ 没有匹配模板，转双 Agent 生成…");
          setProgress(15);
        }
        break;
      case "rendering":
        setStage("② 正在渲染参数化模板…");
        setProgress(75);
        break;
      case "planner":
        setStage("② Planner 正在拆解物理量与参数区间…");
        setProgress(30);
        setAgentStatus("PLANNING");
        break;
      case "coder":
        setStage("③ Coder 正在编写 Canvas 画布代码…");
        setProgress(55);
        setAgentStatus("CODING");
        break;
      case "cache_hit":
        setStage("⚡ 命中缓存，直接复用上次结果…");
        setProgress(90);
        break;
      case "tick":
        // 后端心跳：让进度条在长任务里继续挪，别停在原地
        setProgress((p) => Math.min(94, p + 3));
        break;
      case "arxiv":
        setStage("📄 已抓到论文摘要，正在理解论文机制…");
        setProgress(20);
        break;
      default:
        break;
    }
  };

  const handleGenerate = async (inputPrompt = prompt) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const timeoutId = setTimeout(() => ctrl.abort(), 120_000); // 后端卡死时别一直转圈

    setLoading(true);
    setStage("① 正在连接后端…");
    setProgress(4);
    setPaper(null);
    try {
      setError("");
      const res = await fetch(`${API_BASE}/api/generate/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: inputPrompt }),
        signal: ctrl.signal,
      });
      if (!res.ok || !res.body) {
        // 后端可能还是旧版本（没有 /stream），退回普通接口
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let final: Record<string, unknown> | null = null;

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let split;
        while ((split = buffer.indexOf("\n\n")) >= 0) {
          const frame = buffer.slice(0, split);
          buffer = buffer.slice(split + 2);
          const line = frame.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          let payload: { stage: string; detail?: string; template?: string };
          try {
            payload = JSON.parse(line.slice(5).trim());
          } catch {
            continue;
          }
          if (payload.stage === "error") throw new Error(payload.detail || "生成失败");
          if (payload.stage === "done") {
            final = payload as Record<string, unknown>;
            setProgress(100);
            setAgentStatus("READY");
            continue;
          }
          applyStage(payload);
        }
      }

      if (!final) throw new Error("连接中断，没有收到结果");
      const data = final as {
        plan: LabPlan;
        html: string;
        mode: string;
        template?: string | null;
        elapsed_ms?: number;
        cached?: boolean;
        arxiv?: { id: string; title: string; url: string } | null;
      };
      setPlan(data.plan);
      setHtmlCode(data.html);
      setGuess(null);
      setSplitNonce((n) => n + 1);
      setRestored(false);
      setPaper(data.arxiv ?? null);
      setEngine({
        mode: data.mode === "template" ? "template" : "agent",
        template: data.template ?? null,
        ms: data.elapsed_ms ?? 0,
        cached: Boolean(data.cached),
      });
      setViewMode("preview");
      // 刷新页面不该丢掉刚生成的实验
      try {
        localStorage.setItem(
          "scicanvas:last",
          JSON.stringify({ prompt: inputPrompt, plan: data.plan, html: data.html, engine: data })
        );
      } catch {
        /* 隐私模式或超额，忽略 */
      }
    } catch (err) {
      const e = err as Error;
      if (e.name === "AbortError") {
        setError("已取消（或等待超过 120 秒）。可以重试，或换个更具体的描述。");
      } else {
        setError(`生成失败：${e.message}。请确认后端已在 ${API_BASE} 启动。`);
      }
    } finally {
      clearTimeout(timeoutId);
      // 只有"当前这一轮"结束时才收掉 loading，否则会误关后发起的请求
      if (abortRef.current === ctrl) setLoading(false);
    }
  };

  // 恢复上次会话的实验（只跑一次）
  useEffect(() => {
    try {
      const raw = localStorage.getItem("scicanvas:last");
      if (!raw) return;
      const saved = JSON.parse(raw);
      if (!saved?.html) return;
      setHtmlCode(saved.html);
      setPlan(saved.plan ?? null);
      setPrompt(saved.prompt ?? "");
      if (saved.engine) {
        setEngine({
          mode: saved.engine.mode === "template" ? "template" : "agent",
          template: saved.engine.template ?? null,
          ms: saved.engine.elapsed_ms ?? 0,
          cached: Boolean(saved.engine.cached),
        });
      }
      setRestored(true);
    } catch {
      /* 坏数据直接忽略 */
    }
  }, []);
  // 等待期间计时：实测 25–30s，必须让用户看到「还在动」，否则会被当成卡死
  useEffect(() => {
    if (!loading) {
      setElapsed(0);
      return;
    }
    const startedAt = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(id);
  }, [loading]);

  // 监听沙盒内部 JS 报错并触发自动自愈修复
  // 同一份产物最多自愈 2 次：超过则停止，避免「修不好 -> 再报错 -> 再修」的无限循环
  const healBudget = useRef(2);
  useEffect(() => {
    const handleMessage = async (event: MessageEvent) => {
      // 画布内直接抓握后，底座把新参数值回传给宿主
      if (event.data?.type === "SYNC_FROM_CANVAS") {
        setCanvasSync({ key: String(event.data.key), value: Number(event.data.value) });
        return;
      }
      if (event.data?.type === "SCICANVAS_ERROR" && htmlCode && !fixing) {
        if (healBudget.current <= 0) {
          setError("沙盒多次自愈仍未通过，已停止自动修复。请调整提示词后重新生成。");
          return;
        }
        healBudget.current -= 1;
        setFixing(true);
        setAgentStatus("HEALING");
        setHealCount((n) => n + 1);
        try {
          const res = await fetch(`${API_BASE}/api/fix`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              html: htmlCode,
              error: `${event.data.message} at line ${event.data.line}`,
              // 带上行号，后端就只回传出错附近那一段，省 80%+ 的 token
              line: Number(event.data.line) || undefined,
            }),
          });
          const data = await res.json();
          if (res.ok && data.html) setHtmlCode(data.html);
        } finally {
          setFixing(false);
          setAgentStatus("READY");
        }
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [htmlCode, fixing]);

  // 画布回传的提示自动消失
  useEffect(() => {
    if (!canvasSync) return;
    const id = setTimeout(() => setCanvasSync(null), 1800);
    return () => clearTimeout(id);
  }, [canvasSync]);
  // 向沙盒广播指令（对比模式下有两块，一起发）
  const postToSandbox = (payload: Record<string, unknown>) => {
    document.querySelectorAll("iframe").forEach((f) => {
      f.contentWindow?.postMessage(payload, "*");
    });
  };
  // 混沌注入：把参数推到物理极限（由底座决定推到哪个方向）
  const handleChaos = () => postToSandbox({ type: "CHAOS" });
  // 一键导出单文件交互式 HTML 闪卡
  const handleDownloadHtml = () => {
    if (!htmlCode) return;
    // 导出的卡带会被人转发，塞一个回链当"出处"，也顺便给项目导流
    const credit =
      '<a href="https://github.com/scicanvas/scicanvas" target="_blank" rel="noreferrer" ' +
      'style="position:fixed;bottom:10px;right:12px;z-index:999;font:11px/1.6 ui-monospace,monospace;' +
      'color:#38bdf8;background:rgba(2,6,23,.85);border:1px solid #38bdf8;padding:3px 9px;' +
      'text-decoration:none;box-shadow:0 0 12px rgba(56,189,248,.3)">⚡ Powered by SciCanvas</a>';
    const withCredit = htmlCode.includes("Powered by SciCanvas")
      ? htmlCode
      : htmlCode.replace(/<\/body>/i, `${credit}</body>`);

    // 导出的文件里，公式原本是纯文本。用 KaTeX 的 MathML 输出替换掉——
    // MathML 是浏览器原生支持的，不需要带 CSS、不需要字体文件，单文件依然自包含。
    const formula = plan?.formula_latex?.trim();
    let mathml = "";
    if (formula) {
      try {
        mathml = katex.renderToString(toLatex(formula), {
          output: "mathml",
          throwOnError: false,
          displayMode: false,
        });
      } catch {
        mathml = "";
      }
    }
    const injectMath = mathml
      ? "<script>(function(){var ml=" +
        JSON.stringify(mathml) +
        ",t=" +
        JSON.stringify(formula) +
        ";var n=document.querySelectorAll('span,div,h1,h2,p,strong');" +
        "for(var i=0;i<n.length;i++){if(n[i].children.length===0&&n[i].textContent.trim()===t){n[i].innerHTML=ml;break;}}})();</script>"
      : "";
    const finalHtml = injectMath ? withCredit.replace(/<\/body>/i, `${injectMath}</body>`) : withCredit;

    const blob = new Blob([finalHtml], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${plan?.title || "scicanvas-lab"}.html`;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col relative">
      {/* 背景：径向光晕 + 工程网格，只做装饰不接事件 */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            "radial-gradient(900px 520px at 18% -8%, rgba(56,189,248,0.10), transparent 60%)," +
            "radial-gradient(760px 480px at 92% 4%, rgba(129,140,248,0.08), transparent 62%)",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-0 opacity-[0.16]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(148,163,184,.14) 1px, transparent 1px)," +
            "linear-gradient(90deg, rgba(148,163,184,.14) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(circle at 50% 0%, black, transparent 72%)",
          WebkitMaskImage: "radial-gradient(circle at 50% 0%, black, transparent 72%)",
        }}
      />

      {/* 顶部指挥条 */}
      <header className="relative z-20 h-14 shrink-0 border-b border-slate-800/80 px-5 flex items-center justify-between bg-slate-950/70 backdrop-blur">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xl">⚗️</span>
          <h1 className="text-base font-semibold tracking-tight bg-gradient-to-r from-cyan-300 to-indigo-300 bg-clip-text text-transparent whitespace-nowrap">
            SciCanvas
          </h1>
          <span className="hidden md:inline text-[10px] font-mono tracking-[0.18em] text-slate-500">
            HOLOGRAPHIC LAB
          </span>
          <span className="hidden sm:inline-flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300/90 border border-cyan-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            DeepSeek · DSH
          </span>
          {engine && (
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full border ${
                engine.mode === "template"
                  ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/25"
                  : "bg-indigo-500/10 text-indigo-300 border-indigo-500/25"
              }`}
              title={engine.mode === "template" ? "命中参数化模板，生成稳定且快" : "未命中模板，走双 Agent 自由生成"}
            >
              {engine.mode === "template"
                ? `模板 · ${engine.template} · ${(engine.ms / 1000).toFixed(1)}s`
                : `双 Agent · ${(engine.ms / 1000).toFixed(1)}s`}
              {engine.cached && <span className="ml-1.5 opacity-80">· 缓存命中</span>}
            </span>
          )}
          {paper && (
            <a
              href={paper.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs px-2.5 py-0.5 rounded-full border bg-sky-500/10 text-sky-300 border-sky-500/25 hover:bg-sky-500/20 transition max-w-[280px] truncate"
              title={`arXiv:${paper.id} · ${paper.title}`}
            >
              📄 arXiv:{paper.id}
            </a>
          )}
        </div>
        {htmlCode && (
          <div className="flex gap-3">
            {viewMode === "preview" && (
              <button
                onClick={() => {
                  setSplit((s) => !s);
                  setSplitNonce((n) => n + 1);
                }}
                title="两块独立沙盒跑同一份代码，可分别拖滑块对比参数影响"
                className={`px-3 py-1.5 text-xs rounded-lg border transition ${
                  split
                    ? "bg-emerald-600/20 border-emerald-500/40 text-emerald-300"
                    : "bg-slate-800 hover:bg-slate-700 border-slate-700"
                }`}
              >
                {split ? "⇄ 对比中" : "⇄ 对比模式"}
              </button>
            )}
            {split && viewMode === "preview" && (
              <button
                onClick={() => setSplitNonce((n) => n + 1)}
                className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700"
              >
                ↺ 同步重置
              </button>
            )}
            <button
              onClick={() => setViewMode(viewMode === "preview" ? "code" : "preview")}
              className="px-3 py-1.5 text-xs rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700"
            >
              {viewMode === "preview" ? "查看源码" : "返回交互沙盒"}
            </button>
            <button
              onClick={handleDownloadHtml}
              className="px-3 py-1.5 text-xs rounded-lg bg-cyan-600 hover:bg-cyan-500 font-medium"
            >
⬇️ 导出独立 HTML 实验室
            </button>
          </div>
        )}
      </header>
      {error && (
        <div className="mx-6 mt-4 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2.5 text-xs text-rose-200">
          {error}
        </div>
      )}
      {/* 主体：左侧控制台 + 右侧舞台 */}
      <main className="relative z-10 flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[368px_minmax(0,1fr)] gap-4 p-4">
        {/* 左侧控制台 */}
        <div className="flex flex-col gap-3 min-h-0 lg:overflow-y-auto lg:pr-1">
          <div className="relative bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex flex-col gap-3 backdrop-blur-sm">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono tracking-[0.22em] text-cyan-400/80">
                01 / INPUT
              </span>
              <span className="text-[10px] font-mono text-slate-600">CONCEPT · LAW · PAPER</span>
            </div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={5}
              className="w-full rounded-lg bg-slate-950 border border-slate-800 p-3 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
              placeholder="例如：演示傅里叶级数如何用多个旋转圆合成方波… 也可以直接贴 arXiv:1706.03762"
            />
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setPrompt(item.prompt);
                    handleGenerate(item.prompt);
                  }}
                  className="text-xs px-2.5 py-1.5 rounded-md bg-slate-800/80 hover:bg-slate-800 text-slate-300 border border-slate-700/60 transition"
                >
                  {item.label}
                </button>
              ))}
            </div>
            {loading ? (
              <button
                onClick={() => abortRef.current?.abort()}
                className="mt-2 w-full py-2.5 rounded-lg bg-rose-600/80 hover:bg-rose-600 font-semibold text-sm shadow-lg transition"
              >
                ✕ 取消生成（已等待 {elapsed}s）
              </button>
            ) : (
              <MagneticHoloButton
                onClick={() => handleGenerate()}
                className="mt-2 w-full py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 font-semibold text-sm shadow-lg transition"
              >
                ✨ 立即生成 2D 互动实验室
              </MagneticHoloButton>
            )}
          </div>
          {restored && (
            <div className="rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-[11px] text-slate-400 flex items-center justify-between">
              <span>已恢复上次实验（存在本机浏览器里）</span>
              <button
                onClick={() => {
                  localStorage.removeItem("scicanvas:last");
                  setRestored(false);
                }}
                className="text-slate-500 hover:text-slate-300 underline"
              >
                清空
              </button>
            </div>
          )}
          {/* 科学蓝图与反直觉挑战卡片 */}
          {plan && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 flex flex-col gap-3 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono tracking-[0.22em] text-indigo-400/80">
                  02 / BLUEPRINT
                </span>
                <span className="text-[10px] font-mono text-slate-600">PLANNER OUTPUT</span>
              </div>
              <div>
                <h2 className="text-base font-bold text-cyan-400 leading-tight">{plan.title}</h2>
                <p className="text-xs text-slate-400 mt-1">{plan.subtitle}</p>
              </div>
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-indigo-300">
                <span className="font-mono text-slate-400">🧮 核心定律：</span>
                <MathFormula tex={plan.formula_latex} className="text-sm text-indigo-200" />
              </div>
              {plan.intuition_challenge && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-200">
                  <div className="font-bold mb-1">🤯 直觉挑战</div>
                  <p className="leading-relaxed">{plan.intuition_challenge}</p>
                  {guess ? (
                    <p className="mt-2 text-emerald-300">
                      已锁定猜测：<b>{guess}</b>
                      <span className="text-emerald-400/70"> · 现在去右侧拖动滑块验证</span>
                    </p>
                  ) : (
                    <>
                      <p className="mt-2 text-amber-300/70">先猜一猜，别急着拖滑块：</p>
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {["会变大 ↑", "会变小 ↓", "基本不变 →"].map((g) => (
                          <button
                            key={g}
                            onClick={() => setGuess(g)}
                            className="px-2.5 py-1 rounded-md bg-amber-500/15 hover:bg-amber-500/30 border border-amber-500/40 text-amber-100 transition"
                          >
                            {g}
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
        {/* 右侧交互沙盒：舞台 */}
        <div className="relative flex flex-col min-h-[600px] min-w-0">
          {/* 四角 HUD 括号 */}
          <div aria-hidden className="pointer-events-none absolute inset-0 z-20">
            <span className="absolute left-0 top-0 w-4 h-4 border-l border-t border-cyan-400/50" />
            <span className="absolute right-0 top-0 w-4 h-4 border-r border-t border-cyan-400/50" />
            <span className="absolute left-0 bottom-0 w-4 h-4 border-l border-b border-cyan-400/50" />
            <span className="absolute right-0 bottom-0 w-4 h-4 border-r border-b border-cyan-400/50" />
          </div>
          {/* 画布抓握回传的提示 */}
          {canvasSync && (
            <div className="absolute bottom-4 left-4 z-30 px-2.5 py-1 rounded-md bg-cyan-500/15 border border-cyan-500/40 text-cyan-200 text-[10px] font-mono tracking-wide">
              ⇕ 画布同步 · {canvasSync.key} = {canvasSync.value}
            </div>
          )}
          {fixing && (
            <div className="absolute top-3 right-3 z-30 px-3 py-1 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs animate-pulse">
🩹 检测到沙盒异常，Self-Healing Agent 正在自动热修复代码...
            </div>
          )}
          <HoloCockpit
            status={agentStatus}
            healCount={healCount}
            chaosAvailable={Boolean(htmlCode)}
            onChaos={handleChaos}
          >
          {!htmlCode ? (
            loading ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <div className="w-full max-w-md space-y-5">
                  <div className="text-5xl">⚗️</div>
                  <p className="text-sm font-medium text-slate-200">
                    {stage || "准备中…"}
                  </p>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-indigo-500 transition-all duration-500"
                      style={{ width: `${Math.max(4, Math.min(100, progress))}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span>阶段进度来自后端实时推送</span>
                    <span className="font-mono tabular-nums text-cyan-400">已用时 {elapsed}s</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-8 text-center">
                <div className="text-5xl mb-3">🧪</div>
                <p className="text-sm">点击左侧预设案例或输入任意科学概念</p>
                <p className="mt-1.5 text-xs text-slate-600">10 秒出科学蓝图，实测约 30 秒出可玩沙盒</p>
              </div>
            )
          ) : viewMode === "preview" ? (
            split ? (
              <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-3 p-3">
                {(["A", "B"] as const).map((tag) => (
                  <div
                    key={`${tag}-${splitNonce}`}
                    className="relative rounded-lg overflow-hidden border border-slate-800 bg-slate-950"
                  >
                    <span className="absolute top-2 left-2 z-10 px-2 py-0.5 rounded-md bg-slate-900/90 border border-slate-700 text-[11px] font-mono text-cyan-300">
                      {tag}
                    </span>
                    <iframe
                      srcDoc={htmlCode}
                      title={`SciCanvas Sandbox ${tag}`}
                      sandbox="allow-scripts"
                      className="w-full h-full border-0 bg-slate-950"
                    />
                  </div>
                ))}
              </div>
            ) : (
              <iframe
                srcDoc={htmlCode}
                title="SciCanvas Sandbox"
                sandbox="allow-scripts"
                className="w-full flex-1 border-0 bg-slate-950"
              />
            )
          ) : (
            <pre className="p-4 text-xs font-mono text-emerald-400 overflow-auto flex-1 bg-slate-950">
              {htmlCode}
            </pre>
          )}
          </HoloCockpit>
        </div>
      </main>
    </div>
  );
}
