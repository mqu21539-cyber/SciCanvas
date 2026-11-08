# 回归测试

一条命令跑完全部可自动化的验证：

```bash
node tests/run-all.mjs          # 全量（约 2–3 分钟）
node tests/run-all.mjs --fast   # 只跑不需要真实 API 的快速项
node tests/run-all.mjs --only 04
node tests/run-all.mjs --list
```

每个用例自己判断前置条件，不满足就 **SKIP**（退出码 2），不会把缺环境当成失败。

---

## 用例清单

| # | 用例 | 依赖 | 大概耗时 |
| :-- | :--- | :--- | :--- |
| 00 | 后端冒烟：路由、参数校验、桩客户端跑通双 Agent | Python + venv | 1 s |
| 01 | 插件契约：dsh 的 `defineTool` 编译 + 契约断言 | `@deepseek-ai/dsh-tools` | 1 s |
| 02 | 混合路由：模板命中快、未命中回落、strategy 生效、缓存命中 | 后端 + **真实 API Key** | 60 s |
| 03 | 模板渲染 + 浏览器验证（无异常 / canvas 有像素 / 滑块） | Chrome + Python | 25 s |
| 04 | 自愈链路端到端（真实生成 → 注入错误 → 重渲染） | 后端 + 前端 + Chrome + Key | 60 s |
| 05 | 前端路由徽标（输入单摆 → 模板快路径） | 后端 + 前端 + Chrome + Key | 10 s |
| 06 | 展厅清单一致性（登记的文件都在、id 不重复、降级清单无过期项） | 无 | 0.1 s |
| 07 | 交互功能：先猜后试、双沙盒对比、刷新恢复、取消生成 | 后端 + 前端 + Chrome + Key | 15 s |
| 08 | arXiv 摘要直读：编号识别 6 例 + 真抓真生成 | 后端 + Key + 能连 arXiv | 30 s |

**附带工具**（不参与 `run-all`）

| 命令 | 用途 |
| :--- | :--- |
| `node tests/check-html.mjs <file.html>` | 单独验证一个产物：是否报错、画布是否真的画了东西 |
| `node tests/check-fps.mjs <file.html> [秒]` | 量某个实验的渲染帧率（改模板后看有没有掉帧） |

---

## 前置条件怎么满足

**Chrome**：自动探测 Chrome/Edge 的常见安装路径；找不到时用 `CHROME_PATH` 指定。

**dsh-tools**（01 需要）：优先用裸标识符解析（在 dsh profile 内运行即可）。否则按顺序尝试：

1. 环境变量 `DSH_TOOLS_PATH=.../@deepseek-ai/dsh-tools/lib/index.js`
2. 仓库内 `.probe/probe/node_modules/...`
3. `.probe/asar/dsh/node_modules/...`

本地抽取（只读 app.asar，产物在 `.probe/`，已 gitignore）：

```bash
node tools/probe-dsh-asar.mjs
```

若插件自身解析不到依赖，01 会 SKIP 并提示——需要让 `plugins/dsh-plugin-scicanvas/node_modules`
指向 dsh 的 node_modules（或在 profile 内运行）：

```powershell
New-Item -ItemType Junction -Path "\dsh-plugin-scicanvas\node_modules" `
  -Target "C:\Users\<you>\AppData\Local\Programs\DeepSeek Harness\resources\app.asar.unpacked\dsh\node_modules"
```

**后端 / 前端**：02–05 需要它们在线

```bash
cd backend && .venv/Scripts/python -m uvicorn main:app --port 8010
cd frontend && pnpm dev
```

**真实 API Key**：02、04、05 会真的调 DeepSeek（合计约 3 次调用）。不想花钱就跑 `--fast`。

---

## 环境变量

| 变量 | 用途 |
| :--- | :--- |
| `SCICANVAS_PYTHON` | 指定 Python（默认找 `backend/.venv`） |
| `CHROME_PATH` | 指定浏览器可执行文件 |
| `DSH_TOOLS_PATH` | 指向 `@deepseek-ai/dsh-tools/lib/index.js` |
| `SCICANVAS_GEN_TIMEOUT` | 04 里等生成的上限秒数（默认 150） |

---

## 自己加一个用例

1. 在 `tests/` 建 `06-xxx.mjs` 或 `06-xxx.py`，用 `lib/assert.mjs` 的 `suite()` 输出结果，
   `process.exit(t.done())`（0 过 / 1 失败）。
2. 在 `run-all.mjs` 的 `TESTS` 数组里加一行（`slow: true` 表示 `--fast` 时跳过）。

浏览器类用例直接复用 `lib/browser.mjs`：

```js
import { withChrome, waitHydrated, startGeneration } from './lib/browser.mjs'
await withChrome(async ({ newPage }) => {
  const cdp = await newPage('http://localhost:3000')
  await waitHydrated(cdp)        // 别在水合完成前点击，否则是空点
  const state = await startGeneration(cdp)   // 会重试直到真的启动
})
```

> **水合竞态是个坑**：dev 模式首次访问要先编译，DOM 先到、事件监听后到。
> 早期用例直接 `click()` 后立刻断言，会偶发假失败。上面两个 helper 就是为此加的。

---

## 说明

- 这些测试**不 mock 浏览器**：canvas 是否真的画了东西、自愈是否真的改了 DOM，都是读真实像素/属性得出的。
- 04 注入的错误是合成的（向页面 `postMessage` 一条 `SCICANVAS_ERROR`），它验证的是**页面到修复接口的闭环**，
  不是"模型修某个具体 bug 的能力"——后者要靠人工抽检物理正确性。