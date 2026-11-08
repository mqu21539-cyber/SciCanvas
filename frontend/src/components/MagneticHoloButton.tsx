"use client";

import React, { useRef, useState } from "react";

/**
 * 磁吸按钮：指针靠近时按钮轻微向指针偏移，离开时带弹簧回位。
 *
 * 相比宝典里的版本改了两处：
 * 1. 外面套一圈「热区」——真正的磁场半径要大于按钮本身，否则鼠标没碰到按钮就不会吸；
 * 2. 用 CSS 的 cubic-bezier 回位代替线性过渡，松手有回弹感。
 *
 * 行为完全沿用调用方的 onClick，不改变任何业务逻辑。
 */
export default function MagneticHoloButton({
  children,
  onClick,
  className = "",
  disabled = false,
  strength = 0.28,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
  strength?: number;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = boxRef.current;
    if (!el || disabled) return;
    const r = el.getBoundingClientRect();
    const dx = e.clientX - (r.left + r.width / 2);
    const dy = e.clientY - (r.top + r.height / 2);
    setOffset({ x: dx * strength, y: dy * strength });
  };

  const reset = () => setOffset({ x: 0, y: 0 });

  return (
    <div
      ref={boxRef}
      onPointerMove={onMove}
      onPointerLeave={reset}
      className="p-2 -m-2 inline-flex"
    >
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className={className}
        style={{
          transform: `translate(${offset.x}px, ${offset.y}px)`,
          transition: "transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1)",
          willChange: "transform",
        }}
      >
        {children}
      </button>
    </div>
  );
}