"use client";

import katex from "katex";
import { useMemo } from "react";
import "katex/dist/katex.min.css";

/**
 * 把模型或模板给出的公式串渲染成排版公式。
 *
 * 输入不一定是标准 LaTeX —— 大多是 `θ'' = -(g/L)sinθ - cθ'`、`Vc(t) = V₀(1 − e^{−t/τ})`
 * 这种「半 Unicode 半公式」的写法。所以先做一层字符归一化，再交给 KaTeX；
 * 万一还是渲染不出来（模型偶尔会写出古怪的式子），就退回等宽文本——宁可丑，不能空。
 */

const CHAR_MAP: Record<string, string> = {
  // 希腊字母
  "α": "\\alpha ", "β": "\\beta ", "γ": "\\gamma ", "δ": "\\delta ", "ε": "\\varepsilon ",
  "θ": "\\theta ", "λ": "\\lambda ", "μ": "\\mu ", "π": "\\pi ", "ρ": "\\rho ",
  "σ": "\\sigma ", "τ": "\\tau ", "φ": "\\varphi ", "ω": "\\omega ", "ψ": "\\psi ",
  "Δ": "\\Delta ", "Ω": "\\Omega ", "Σ": "\\Sigma ", "Φ": "\\Phi ", "Ψ": "\\Psi ",
  "∂": "\\partial ", "∇": "\\nabla ",
  // 运算符与关系
  "−": "-", "·": "\\cdot ", "×": "\\times ", "÷": "\\div ", "≈": "\\approx ",
  "≤": "\\le ", "≥": "\\ge ", "≠": "\\ne ", "→": "\\to ", "∝": "\\propto ",
  "∞": "\\infty ", "√": "\\sqrt ", "∫": "\\int ", "∑": "\\sum ",
  // 上标下标
  "²": "^{2}", "³": "^{3}", "⁻": "^{-}", "₀": "_{0}", "₁": "_{1}", "₂": "_{2}",
  "ᵢ": "_{i}", "ₙ": "_{n}", "ₖ": "_{k}",
};

function toLatex(raw: string): string {
  const text = raw.replace(/\$/g, "").trim();
  if (!text) return "";
  let out = "";
  for (const ch of text) {
    out += CHAR_MAP[ch] ?? ch;
  }
  // 函数名要正体，否则 sinθ 会被排成斜体的 s·i·n
  out = out.replace(/\b(sin|cos|tan|log|ln|exp|max|min|det)\b/g, "\\$1 ");
  return out;
}

export default function MathFormula({ tex, className = "" }: { tex: string; className?: string }) {
  const rendered = useMemo(() => {
    try {
      const html = katex.renderToString(toLatex(tex), {
        throwOnError: true,
        displayMode: false,
        output: "html",
        strict: "ignore",
      });
      return { ok: true as const, html };
    } catch {
      return { ok: false as const, html: "" };
    }
  }, [tex]);

  if (!rendered.ok) {
    return <span className={`font-mono ${className}`}>{tex}</span>;
  }
  return (
    <span
      className={className}
      // KaTeX 的输出由它自己生成，不含外部输入
      dangerouslySetInnerHTML={{ __html: rendered.html }}
    />
  );
}