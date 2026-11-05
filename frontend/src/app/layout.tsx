import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SciCanvas — 课本与论文秒变 2D 互动实验室",
  description:
    "Turn any textbook concept or arXiv paper into an interactive 2D physics & math simulation lab in 10 seconds.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">{children}</body>
    </html>
  );
}
