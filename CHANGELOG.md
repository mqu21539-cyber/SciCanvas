# 变更记录

遵循 [语义化版本](https://semver.org/lang/zh-CN/)。本项目在正式发版前按能力阶段递增。

---

## [0.8.0] — 2026-11-05

### 新增
- **arXiv 摘要直读**：输入里出现 `arXiv:1706.03762`（或 `arxiv.org/abs/...` 链接、`hep-th/9901001`
  这类老编号）时，后端自动调 arXiv API 抓标题与摘要再生成，不用手抄正文。
  抓取实测 **0.6 s**，端到端 **29.1 s**，产物 20,626 字符。
  离线或抓取失败自动回落到用户原文；响应带 `arxiv{id,title,url}`，前端显示出处徽标。
  新增 `tests/08-arxiv.py`（编号识别 6 例 + 联网真抓真生成，断网时跳过而不是判失败）。

---

## [0.7.0] — 2026-11-05

### 变更
- **默认端口 8000 → 8010**。原因见 0.6.1 的排查：本机 8000 端口会让 SSE 首帧多等 1–3 秒，
  同代码换到 8010 后，**非浏览器客户端**（插件、curl、测试脚本）首帧稳定在 2–7 毫秒。
  涉及前端 `API_BASE`、两个启停脚本、`cordis.yml`、插件默认值、测试与文档，已全部对齐。

### 已知遗留
- **浏览器内仍有约 1.2 秒首帧延迟**，且与端口、首帧大小（试过 2KB / 64KB）都无关：
  服务端日志显示 `0.002s` 就产出了首帧，裸 socket 也是 2ms 收到，只有 Chrome 的 `fetch`
  要等 1.2–1.4 秒。普通接口（`/api/health`）在浏览器里只要 10ms，所以不是 CORS、不是代理
  （`ProxyEnable=0`），怀疑是本机安全软件对"无 Content-Length 的 chunked 响应体"做了缓冲。
  未找到代码侧解法；UI 已有「正在连接后端…」占位，不至于白屏。

---

## [0.6.1] — 2026-11-05

### 排查
- **SSE 首帧延迟**：一度误判为 uvicorn `httptools` 实现的问题，实测下来与该实现无关。
  控制变量后（同一份代码、单监听、统一口径"第一帧 data: 到达时间"）：

  | 端口 | 首帧 |
  | :--- | :--- |
  | 8000 | 1.0–3.0 s（重启、换 `--http h11` 均如此） |
  | 8002 / 8003 / 8021 | 0.002–0.007 s |

  结论：是本机 **8000 端口**被外部软件（防火墙/杀软）拖慢，与代码实现无关。
  换端口即可，已写进 README 排障提示。

---

## [0.6.0] — 2026-11-05

### 新增
- **SSE 流式进度** `POST /api/generate/stream`：分诊 / Planner / Coder 三个阶段实时推给前端，
  长任务每 3 秒补一个心跳；进度条从"按秒数猜"变成"按后端口径走"。
- **模板库 6 → 10**：新增 `fourier`（傅里叶合成方波）、`rc`（RC 充放电）、`heat`（一维热传导）、
  `montecarlo`（蒙特卡洛估 π）。四个模板均通过真实浏览器验证（无异常 / 画布有像素 / 滑块正常）。
- `check-fps.mjs`：量任意实验的渲染帧率，改模板后复查用。

### 变更
- 前端加载态改为显示真实阶段文案，并在首个事件到达前显示「正在连接后端…」。

### 未采纳（有实测依据）
- **自愈片段化**：只回传出错附近代码，实测省 67% 输入 token、快 7 倍，但三种拼接设计
  （整段重写 / diff 合并 / 补丁 JSON）都会在「删掉一行声明」这类真实故障上产出坏文件
  （语法错或画面全空），而服务端没有 JS 运行时可以验证。**默认关闭**，
  留 `SCICANVAS_SNIPPET_FIX=1` 作实验开关，详见 `backend/agents.py` 注释。

---

## [0.5.0] — 2026-11-05

### 新增
- **生成结果缓存** `backend/cache.py`：按「策略 + 提示词」哈希落盘（7 天 TTL、原子写）。
  实测同一提示词第二次生成 **28.08 s → 0.04 s、0 token**。
  新增 `GET /api/cache`（条数/占用）、`DELETE /api/cache`（清空）；`SCICANVAS_NO_CACHE=1` 可绕过。
- **可取消 + 超时**：生成中按钮变为「取消生成（已等待 Ns）」，底层用 `AbortController`；
  120 秒无响应自动中止；新一轮生成会自动取消上一轮，避免两个结果互相覆盖。
- **刷新不丢**：成功后把上次实验存进 `localStorage`，重开页面自动恢复，并给出「已恢复」提示与清空入口。
- **测试基建**：`waitHydrated()` / `startGeneration()` 消除 dev 模式的水合竞态（点击空点曾导致用例假失败）。

### 变更
- 引擎徽标在命中缓存时追加「· 缓存命中」。

---

## [0.4.0] — 2026-11-05

### 新增
- **先猜后试挑战卡**：生成后先让用户押一个预测（会变大 / 会变小 / 基本不变），选定才提示去拖滑块验证。
- **双沙盒同屏对比**：同一份实验代码开两块独立 iframe，左右分别调参，支持一键同步重置。
- **README 素材**：`assets/demo.gif`（6 个真实实验，1.1 MB）、`assets/architecture.svg`（手写架构图）、`assets/social-preview.png`（1280×640）。
- **文档**：`docs/执行清单.md`（把文档二的空表换成实际进度）、`CONTRIBUTING.md`、`CHANGELOG.md`。
- **测试 07**：交互功能的浏览器级验证（猜卡 + 对比模式）。

### 修复
- 洛伦兹模板轨迹采样过稀，蝴蝶连成放射状折线；改为逐子步采样，并加 4200 步预热让首帧就是完整吸引子。
- 洛伦兹投影改为等比缩放，不再把图形压扁。

---

## [0.3.0] — 2026-11-05

### 新增
- **混合路由** `backend/router.py`：模板命中走 B（约 2 秒），未命中回落双 Agent（20–30 秒）；`strategy=auto|template|agent` 可覆盖。
- `/api/templates`、`/api/health` 增加模板清单。
- **B 模板库 2 → 6**：新增 `wave`（行波叠加/驻波）、`efield`（场线积分）、`orbit`（开普勒轨道）、`lorenz`（RK4 双轨混沌）。
- 前端引擎徽标：`模板 · oscillator · 1.3s` / `双 Agent · 19.7s`。
- `tests/` 一键回归（00–06）、`tools/probe-dsh-asar.mjs`。

### 修复
- 前端 favicon 404（新增 `src/app/icon.svg`）。
- 进度条阈值按实测耗时校准（90s → 32s）。

---

## [0.2.0] — 2026-11-05

### 变更
- **插件按 dsh 真实契约重写**：从「npm 包 + cordis.yml + `ctx.tool.register`」改为
  Host bundle（`dsh.bundle.patch`）+ `inject = ['tools']` + `ctx.tools.register(defineTool(...))`。
  依据是 dsh 内置的 `cordis-plugin-development` 技能与 `dsh-tool-todo` 实现。
- 移除 TypeScript 构建链与 `cordis` 依赖，直接跑 ESM `index.js`。

### 新增
- `probe.mjs`：用 dsh 自己的 `defineTool` / `validateJsonSchemaValue` 校验插件，21 项断言。
- 插件安装进 desktop profile；生成即登记 `gallery/manifest.json`（幂等 upsert，原子写）。

### 修复
- 中文标题 slug 化后为空，导致所有实验覆盖同一个 `scicanvas-lab.html`；改为回落到本地时间戳。

---

## [0.1.0] — 2026-11-05

### 新增
- 从【文档二】落地完整骨架：FastAPI 双 Agent、Next.js 工作台、静态展厅、GitHub Actions、LICENSE。
- 自愈闭环：`window.onerror` → `POST /api/fix` → 重渲染，同产物最多 2 次。
- 5 个真实生成的展厅实验。

### 修复（相对原教程）
- `uses:actions/...` 缺空格导致 workflow 解析失败。
- `cordis@^4.9.0` 版本不存在（最高 `4.0.0-rc.12`）。
- `openai==1.50` 与 httpx ≥0.28 不兼容（`proxies` 参数被移除）。
- 无 API Key 时 `OpenAI()` 在 import 阶段抛异常，服务起不来。
- `allow_origins=["*"]` + `allow_credentials=True` 被浏览器拒绝。
- 自愈无上限可能无限刷 API。
- 文档正文误粘的生成指令语、写死的 3080 端口、丢失的 emoji。

---

## 关于版本号

- `0.x` 阶段：接口（HTTP、插件工具签名、模板 `META`）仍可能调整。
- `1.0.0` 的条件：插件发布到 npm、Pages 上线、7 个测试在干净环境全绿。