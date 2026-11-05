# 变更记录

遵循 [语义化版本](https://semver.org/lang/zh-CN/)。本项目在正式发版前按能力阶段递增。

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