"use client";

import { useCallback, useRef } from "react";

/**
 * 科幻音效：用 Web Audio 现场合成，不加载任何音频文件。
 *
 * 注意：AudioContext 必须复用。有些实现每次点击都 new 一个，
 * 浏览器上限约 6 个，点几下就彻底没声了。
 */
export function useSciFiSound() {
  const ctxRef = useRef<AudioContext | null>(null);
  const mutedRef = useRef(false);

  const getCtx = useCallback(() => {
    if (typeof window === "undefined") return null;
    if (!ctxRef.current) {
      const Ctor =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return null;
      ctxRef.current = new Ctor();
    }
    if (ctxRef.current.state === "suspended") void ctxRef.current.resume();
    return ctxRef.current;
  }, []);

  const blip = useCallback(
    (freq: number, to: number, dur: number, gain: number, type: OscillatorType = "sine") => {
      if (mutedRef.current) return;
      const ctx = getCtx();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(Math.max(20, to), ctx.currentTime + dur);
      g.gain.setValueAtTime(gain, ctx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
      osc.connect(g);
      g.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + dur + 0.01);
    },
    [getCtx]
  );

  /** 悬停/滑块微调 */
  const playTick = useCallback((freq = 1180) => blip(freq, freq * 1.35, 0.045, 0.035), [blip]);
  /** 面板展开/对比模式切换 */
  const playMatrixShift = useCallback(
    (expand: boolean) => blip(expand ? 240 : 660, expand ? 880 : 180, 0.22, 0.09, "triangle"),
    [blip]
  );
  /** 混沌注入 / 自愈告警 */
  const playAlertPulse = useCallback(() => blip(300, 520, 0.28, 0.075, "sawtooth"), [blip]);

  const toggleMute = useCallback(() => {
    mutedRef.current = !mutedRef.current;
    return mutedRef.current;
  }, []);

  return { playTick, playMatrixShift, playAlertPulse, toggleMute };
}