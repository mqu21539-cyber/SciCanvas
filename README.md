# SciCanvas

把课本段落、公式或论文摘要，变成可拖拽参数、带实时数值的 2D 互动实验沙盒。

本仓库同时存放**两条技术路线**——A 方案已实现可跑，B 方案是已验证思路的原型骨架。

---

## 两条路线

| | **A · 自由生成** ✅ 已实现 | **B · 模板化生成** 🧪 原型 |
| :--- | :--- | :--- |
| **怎么做** | 双 Agent：Planner 拆解物理量 → Coder 直接写整份单文件 HTML | 预置参数化模板库；模型只输出「用哪个模板 + 参数 + 文案」 |
| **模型输出量** | 约 6,900 tokens（500–700 行代码） | 约 300–500 tokens（一段 JSON） |
| **实测耗时** | **25–30 秒**（5 次实测） | 目标 **10–15 秒** |
| **覆盖面** | 任意概念，想生成什么就生成什么 | 仅限已建模板的 6 类仿真 |
| **质量稳定性** | 取决于模型，需抽检物理正确性 | 模板内物理必然正确，不会跑偏 |
| **可维护性** | 改 prompt 即改行为，难调试 | 改模板即改质量，可单元测试 |
| **代码量** | 后端 + 前端 + 插件 + 展厅，完整产品 | 1 个生成器 + N 个模板 |
| **适用场景** | 对外 Demo、冲 GitHub、任意概念 | 教学产品化、批量生成、离线部署 |

> **为什么两个都要**：A 负责"什么都能试"的惊艳感，B 负责"每次都对"的可靠性。
> A 现在就能发布；B 是把 A 的随机性兜住的后手。

---

## 目录

```
D:\SciCanvas\
├── A-自由生成\                 ← 主方案，完整可运行
│   ├── backend\                FastAPI + 双 Agent（Planner / Coder / Fixer）
│   ├── frontend\               Next.js 15 工作台（进度条 / 沙盒 / 自愈 / 导出）
│   ├── dsh-plugin-scicanvas\   DeepSeek Harness 插件
│   ├── gallery\                免服务器静态展厅（4 个真实实验）
│   ├── assets\                 README 演示素材
│   ├── cordis.yml              插件挂载配置
│   └── README.md               A 方案详细说明
├── B-模板化生成\               ← 第二方案，原型
│   ├── generator.py            plan(JSON) → 单文件 HTML
│   ├── templates\              参数化模板库
│   ├── examples\               示例 plan
│   └── README.md               B 方案规格与用法
├── docs\
│   └── 技术可行性评估.md        实测数据、风险清单、成本、剩余工作量
├── .github\workflows\          GitHub Pages 自动部署（指向 A 的 gallery）
├── LICENSE  .gitignore  .gitattributes
└── README.md                   本文件
```

---

## 快速开始（A 方案）

```bash
cd A-自由生成/backend
pip install -r requirements.txt
cp .env.example .env        # 填入 DEEPSEEK_API_KEY
uvicorn main:app --reload --port 8000
```

```bash
cd A-自由生成/frontend
npm install
npm run dev                 # http://localhost:3000
```

**不想装环境？** 直接双击 `A-自由生成/gallery/index.html`，4 个预生成实验立刻可玩。

---

## 快速试玩（B 方案）

```bash
cd B-模板化生成
python generator.py --list                                  # 看可用模板
python generator.py --plan examples/plan-oscillator.json     # 模板 → HTML
python generator.py --text "演示单摆阻尼振动" --out out/demo.html   # 调模型选模板
```

---

## 当前状态

| 模块 | 状态 |
| :--- | :--- |
| A · 双 Agent 生成 | ✅ 5 次真实调用全部成功，产物可运行 |
| A · 前端工作台 | ✅ `next build` 通过，三阶段进度条 + 引擎徽标 |
| A · 静态展厅 | ✅ 4 个实验（3 个由模型现场生成） |
| A · 自愈闭环 | ✅ 真实 Chrome 端到端验证：报错 → /api/fix → 重渲染（9/9） |
| A · dsh 插件 | ✅ 按 dsh 真实契约重写（`ctx.tools` + `defineTool`），契约自测 24/24 |
| 混合路由 | ✅ 模板命中 1.3s，未命中回落 20–27s（4/4） |
| B · 生成器 + 模板 | ✅ 6 个模板，真实浏览器验证 28/28 |

细节与证据见 [技术可行性评估](docs/技术可行性评估.md)。