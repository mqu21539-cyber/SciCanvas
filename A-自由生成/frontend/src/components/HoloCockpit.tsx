"use client";

import React, { useRef, useState } from "react";
import { useSciFiSound } from "../hooks/useSciFiSound";

export type AgentStatus = "IDLE" | "PLANNING" | "CODING" | "HEALING" | "READY";

/**
 * 全息座舱外壳：鼠标追光 + 3D 视差 + 双 Agent 脉冲条。
 *
 * 只包住右侧沙盒区，不动左侧输入区——那里的交互已经被测试覆盖，
 * 加视差反而会让点击目标跟着跑。
 */
export default function HoloCockpit({
  status,
  healCount = 0,
  onChaos,
  chaosAvailable = false,
  children,
}: {
  status: AgentStatus;
  healCount?: number;
  onChaos?: () => void;
  chaosAvailable?: boolean;
  children: React.ReactNode;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ rx: 0, ry: 0 });
  const [locked, setLocked] = useState(false);
  const [glow, setGlow] = useState({ x: 50, y: 40 });
  const { playTick, playMatrixShift, playAlertPulse } = useSciFiSound();

  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = boxRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * 100;
    const y = ((e.clientY - r.top) / r.height) * 100;
    setGlow({ x, y });
    if (!locked) {
      setTilt({ ry: ((x - 50) / 50) * 2.4, rx: -((y - 50) / 50) * 2.0 });
    }
  };

  const chip = (active: boolean, color: string) =>
    `px-2 py-0.5 rounded border transition-all text-[10px] tracking-wider ${
      active
        ? `${color} shadow-[0_0_14px_currentColor] animate-pulse`
        : "border-slate-800 text-slate-500"
    }`;

  return (
    <div
      ref={boxRef}
      onPointerMove={onMove}
      onPointerLeave={() => setTilt({ rx: 0, ry: 0 })}
      className="relative flex-1 flex flex-col min-h-0 overflow-hidden rounded-xl"
      style={
        {
          "--mx": `${glow.x}%`,
          "--my": `${glow.y}%`,
        } as React.CSSProperties
      }
    >
      {/* 鼠标追光 */}
      <div
        className="pointer-events-none absolute inset-0 z-0"
        style={{
          background:
            "radial-gradient(520px circle at var(--mx) var(--my), rgba(56,189,248,0.10), transparent 45%)",
        }}
      />

      {/* 双 Agent 脉冲条 */}
      <div className="relative z-20 flex items-center gap-2 px-3 py-1.5 border-b border-slate-800/80 bg-slate-950/60">
        <span className={chip(status === "PLANNING", "border-purple-400 text-purple-300")}>
          01.PLANNER
        </span>
        <span className="text-sky-600/60 text-[10px]">━━▶</span>
        <span className={chip(status === "CODING", "border-sky-400 text-sky-300")}>
          02.CODER-2.5D
        </span>
        {(status === "HEALING" || healCount > 0) && (
          <>
            <span className="text-amber-500/70 text-[10px]">━━▶</span>
            <span className={chip(status === "HEALING", "border-amber-400 text-amber-300")}>
              ⚡ AST 自愈 #{healCount}
            </span>
          </>
        )}

        <div className="ml-auto flex items-center gap-1.5">
          {chaosAvailable && (
            <button
              onClick={() => {
                playAlertPulse();
                onChaos?.();
              }}
              title="把参数推到物理极限"
              className="px-2 py-0.5 text-[10px] rounded border border-amber-500/60 text-amber-300 hover:bg-amber-400 hover:text-slate-950 transition"
            >
              ⚡ 混沌注入
            </button>
          )}
          <button
            onClick={() => {
              playMatrixShift(!locked);
              setLocked((v) => !v);
              setTilt({ rx: 0, ry: 0 });
            }}
            className="px-2 py-0.5 text-[10px] rounded border border-sky-500/40 text-sky-300 hover:bg-sky-400 hover:text-slate-950 transition"
          >
            {locked ? "🔒 视差锁止" : "🛸 3D 视差"}
          </button>
        </div>
      </div>

      {/* 3D 视差容器 */}
      <div
        className="relative z-10 flex-1 flex flex-col min-h-0"
        style={{
          transform: locked ? "none" : `rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg)`,
          transformStyle: "preserve-3d",
          transition: "transform 0.15s ease-out",
        }}
      >
        {children}
      </div>
    </div>
  );
}