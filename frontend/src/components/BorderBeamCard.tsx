"use client";

import React from "react";

/**
 * 流光边框：一束青色激光沿容器边缘持续游走。
 *
 * 来源是《视觉惊艳度宝典》里的 BorderBeamCard，做了三点适配：
 * 1. 关键帧写在组件内的 <style> 里（不依赖 styled-jsx，也不污染 globals.css）；
 * 2. 默认只画一圈 1.5px 的边，不做 `-inset-[100%]` 那种 3 倍面积的重绘；
 * 3. 尊重 `prefers-reduced-motion`，该关的时候直接不转。
 */
export default function BorderBeamCard({
  children,
  className = "",
  color = "#38bdf8",
  active = true,
  duration = 7,
}: {
  children: React.ReactNode;
  className?: string;
  color?: string;
  active?: boolean;
  duration?: number;
}) {
  return (
    <div className={`relative overflow-hidden rounded-xl ${className}`}>
      <style>{`
        @keyframes scicanvas-beam-spin { to { transform: rotate(1turn); } }
        @media (prefers-reduced-motion: reduce) {
          .scicanvas-beam { animation: none !important; opacity: 0; }
        }
      `}</style>

      {active && (
        <div
          aria-hidden
          className="scicanvas-beam pointer-events-none absolute left-1/2 top-1/2 z-0"
          style={{
            width: "180%",
            aspectRatio: "1 / 1",
            marginLeft: "-90%",
            marginTop: "-90%",
            background: `conic-gradient(from 0deg, transparent 0 74%, ${color} 88%, transparent 96%)`,
            animation: `scicanvas-beam-spin ${duration}s linear infinite`,
            opacity: 0.55,
          }}
        />
      )}

      {/* 中间镂空：只让边框那 1px 透出光，内部保持原来的深色 */}
      <div className="pointer-events-none absolute inset-[1px] z-0 rounded-[11px] bg-slate-950" />

      <div className="relative z-10 flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}