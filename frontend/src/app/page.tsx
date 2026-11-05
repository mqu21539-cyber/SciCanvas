"use client";
import React, { useCallback, useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

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
  const [viewMode, setViewMode] = useState<"preview" | "code">("preview");
  const handleGenerate = async (inputPrompt = prompt) => {
    setLoading(true);
    try {
      setError("");
      const res = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: inputPrompt }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || `HTTP ${res.status}`);
      }
      setPlan(data.plan);
      setHtmlCode(data.html);
      setViewMode("preview");
    } catch (err) {
      setError(`生成失败：${(err as Error).message}。请确认后端已在 ${API_BASE} 启动。`);
    } finally {
      setLoading(false);
    }
  };
  // 等待期间计时：真实耗时 70–170s，必须让用户看到「还在动」，否则会被当成卡死
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
      if (event.data?.type === "SCICANVAS_ERROR" && htmlCode && !fixing) {
        if (healBudget.current <= 0) {
          setError("沙盒多次自愈仍未通过，已停止自动修复。请调整提示词后重新生成。");
          return;
        }
        healBudget.current -= 1;
        setFixing(true);
        try {
          const res = await fetch(`${API_BASE}/api/fix`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              html: htmlCode,
              error: `${event.data.message} at line ${event.data.line}`,
            }),
          });
          const data = await res.json();
          if (res.ok && data.html) setHtmlCode(data.html);
        } finally {
          setFixing(false);
        }
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [htmlCode, fixing]);
  // 一键导出单文件交互式 HTML 闪卡
  const handleDownloadHtml = () => {
    if (!htmlCode) return;
    const blob = new Blob([htmlCode], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${plan?.title || "scicanvas-lab"}.html`;
    a.click();
  };
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* 顶部导航栏 */}
      <header className="border-b border-slate-800 px-6 py-4 flex items-center justify-between bg-slate-900/60 backdrop-blur">
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚗️</span>
          <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-indigo-400 bg-clip-text text-transparent">
            SciCanvas
          </h1>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            Powered by DeepSeek & DSH
          </span>
        </div>
        {htmlCode && (
          <div className="flex gap-3">
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
      {/* 主体分栏 */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6">
        {/* 左侧控制与原理解析区 */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-3">
            <label className="text-sm font-semibold text-slate-300">
              输入课本概念、物理定律或论文摘要：
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={5}
              className="w-full rounded-lg bg-slate-950 border border-slate-800 p-3 text-sm text-slate-200 focus:outline-none focus:border-cyan-500"
              placeholder="例如：演示傅里叶级数如何用多个旋转圆合成方波..."
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
            <button
              onClick={() => handleGenerate()}
              disabled={loading}
              className="mt-2 w-full py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 font-semibold text-sm shadow-lg disabled:opacity-50 transition"
            >
              {loading ? "⏳ 双 Agent 正在推导公式与编写交互画布..." : "✨ 立即生成 2D 互动实验室"}
            </button>
          </div>
          {/* 科学蓝图与反直觉挑战卡片 */}
          {plan && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col gap-3">
              <div>
                <h2 className="text-base font-bold text-cyan-400">{plan.title}</h2>
                <p className="text-xs text-slate-400 mt-1">{plan.subtitle}</p>
              </div>
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-2.5 font-mono text-xs text-indigo-300">
🧮 核心定律：{plan.formula_latex}
              </div>
              {plan.intuition_challenge && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-200">
                  <span className="font-bold">🤯 直觉挑战：</span>
                  {plan.intuition_challenge}
                </div>
              )}
            </div>
          )}
        </div>
        {/* 右侧交互沙盒渲染区 */}
        <div className="lg:col-span-8 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col min-h-[600px] relative">
          {fixing && (
            <div className="absolute top-3 right-3 z-20 px-3 py-1 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs animate-pulse">
🩹 检测到沙盒异常，Self-Healing Agent 正在自动热修复代码...
            </div>
          )}
          {!htmlCode ? (
            loading ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                <div className="w-full max-w-md space-y-5">
                  <div className="text-5xl">⚗️</div>
                  <p className="text-sm font-medium text-slate-200">
                    {elapsed < 15
                      ? "① 正在拆解物理量与参数区间…"
                      : elapsed < 75
                        ? "② 正在编写 Canvas 画布代码…"
                        : "③ 代码较长，仍在生成中（复杂概念会更久）…"}
                  </p>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-indigo-500 transition-all duration-1000"
                      style={{ width: `${Math.min(95, Math.round((elapsed / 90) * 100))}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span>双 Agent 串行生成中，请勿关闭页面</span>
                    <span className="font-mono tabular-nums text-cyan-400">已用时 {elapsed}s</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-500 p-8 text-center">
                <div className="text-5xl mb-3">🧪</div>
                <p className="text-sm">点击左侧预设案例或输入任意科学概念</p>
                <p className="mt-1.5 text-xs text-slate-600">10 秒出科学蓝图，约 90 秒出可玩沙盒</p>
              </div>
            )
          ) : viewMode === "preview" ? (
            <iframe
              srcDoc={htmlCode}
              title="SciCanvas Sandbox"
              sandbox="allow-scripts"
              className="w-full flex-1 border-0 bg-slate-950"
            />
          ) : (
            <pre className="p-4 text-xs font-mono text-emerald-400 overflow-auto flex-1 bg-slate-950">
              {htmlCode}
            </pre>
          )}
        </div>
      </main>
    </div>
  );
}
