# 贡献指南

感谢你想给 SciCanvas 添砖加瓦。这个项目同时有两套实现（A 自由生成 / B 模板化），
改动前先确认你改的是哪一条路线。

## 先跑起来

```bash
# 后端
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
cp .env.example .env        # 填入 DEEPSEEK_API_KEY
.venv/Scripts/python -m uvicorn main:app --port 8010

# 前端
cd frontend
pnpm install && pnpm dev
```

## 提交前必做

```bash
node tests/run-all.mjs --fast     # 约 2 秒，不花钱
node tests/run-all.mjs            # 改了前端/后端/模板时跑全量（会真实调用 API）
```

任何一个 FAIL 都不应提交。SKIP 不算失败，但要在 PR 里说明为什么跳过。

## 目录约定

| 目录 | 放什么 | 不该放什么 |
| :--- | :--- | :--- |
| `backend` | FastAPI、双 Agent、路由 | 前端资源 |
| `frontend` | Next.js 工作台 | 后端逻辑 |
| `plugins/dsh-plugin-scicanvas` | dsh Host bundle | 构建产物（`lib/`、`node_modules/`） |
| `backend/templates` | 每个模板一个 `.py`，暴露 `META` + `build()` | 与模板无关的工具函数 |
| `gallery/labs` | 可离线运行的单文件实验 | 依赖本地服务的页面 |
| `tests` | 可自动化的验证 | 一次性脚本 |

## 加一个 B 模板

复制 `backend/templates/oscillator.py`，只暴露 `META` 和 `build(params, copy)`：

- 控件 `id` 必须与 `controls[].id` 一致
- 指标元素 `id` 必须是 `m_<metrics[].id>`，读数 span 是 `val_<id>`
- 用 `requestAnimationFrame` + **固定步长**积分（不然不同刷新率下轨迹不一致）
- 加完在 `templates/__init__.py` 的 `MODULES` 里注册，然后 `node tests/run-all.mjs --only 03`

## 改插件

dsh 的插件契约与常见 npm 插件不同（`inject = ['tools']`、`defineTool`、字段式参数 schema）。
改之前先看 `plugins/dsh-plugin-scicanvas/README.md` 里的对照表，改完跑：

```bash
node plugins/dsh-plugin-scicanvas/probe.mjs
```

## 提交信息

`<type>(<scope>): <subject>`，type 用 `feat|fix|docs|test|refactor|chore`，
scope 用 `A|B|plugin|gallery|tests|docs`。例：

```
feat(B): 新增双点电荷电场线模板
fix(A): 中文标题生成空 slug 导致产物互相覆盖
```

## 代码风格

- Python：`black` 默认风格，字符串优先中文注释解释"为什么"
- TypeScript：`strict` 已开，不用 `any` 除非真的外部不可控（并写注释）
- 生成的 HTML：单文件、零构建、只允许 Tailwind CDN 一个外部依赖

## 不要提交的东西

`.env`、`.venv`、`node_modules`、`.next`、`assets/_frames`、`.probe/`。
这些都已写进 `.gitignore`，如果 `git status` 里出现它们，说明忽略规则被改坏了。

## 报告问题

带上三样：复现命令、`node tests/run-all.mjs --only XX` 的输出、以及浏览器控制台报错
（沙盒里的报错会被 `window.onerror` 桥接出来，直接复制即可）。