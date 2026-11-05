# dsh-plugin-scicanvas

DeepSeek Harness（`dsh`）插件：把任意科学概念、公式或论文段落变成可拖拽的 2D 互动实验，并直接在浏览器打开。

注册两个工具：

| 工具 | 作用 |
| :--- | :--- |
| `render_science_lab` | 概念/论文 → 单文件交互式 HTML 实验（优先本地 FastAPI 双 Agent，否则直连 DeepSeek） |
| `heal_science_lab` | 已生成的实验报错时，把错误交给修复 Agent 就地修好 |

---

## 真实 API（已按 dsh 源码核对，与早期教程不同）

dsh 的插件不是"npm 包 + cordis.yml + ctx.tool.register"，而是 **bundle**：

| 环节 | 正确做法 | 早期文档的错误 |
| :--- | :--- | :--- |
| 插件形态 | `package.json` 里声明 `dsh.bundle.patch`，配套 `cordis.patch.yml` | 以为是普通 npm 包 + `cordis.yml` |
| 工具服务名 | `inject = ['tools']` → `ctx.tools`（复数） | `ctx.tool.register()`（单数） |
| 定义工具 | `ctx.tools.register(defineTool({...}))`，`defineTool` 来自 `@deepseek-ai/dsh-tools` | 手写 `{name, description, parameters, execute}` 对象 |
| 参数 schema | 字段表：每字段自带 `required: true` | JSON Schema 的 `properties` + `required: [...]` |
| 对象类型 | 必须显式写 `additionalProperties: true/false` | 未提及 |
| 安装 | `plugin_manager` 的 `install_bundle` | 手动维护 `cordis.yml` |

依据：dsh 内置技能 `cordis-plugin-development`（`references/host-plugin.md`）与
`@deepseek-ai/dsh-tool-todo` 的真实实现。

---

## 安装

在本仓库任意会话里，让 dsh 执行：

```
plugin_manager { action: "install_bundle", target: "D:\\SciCanvas\\A-自由生成\\dsh-plugin-scicanvas" }
```

安装后到「设置 → 插件」里应能看到 **SciCanvas 互动实验室**（标题与描述来自 `locale/zh.json`）。

> 需要审批的 `plugin_manager` 动作请按提示批准；`application` 字段为 `applied` 才算真正生效。

## 配置（`cordis.patch.yml`）

```yaml
- insert:
    - id: scicanvas
      name: 'dsh-plugin-scicanvas'
      config:
        backendUrl: 'http://127.0.0.1:8000'   # 本地后端，未启动则自动降级
        outputDir: './scicanvas-labs'          # 产物目录
        galleryManifest: ''                    # 展厅 manifest.json；给了才登记（留空不登记）
        galleryCategory: 'AI 实时生成'          # 登记时的分类前缀
        autoOpenBrowser: true
```

`deepseekApiKey` 可放在 config 或 `DEEPSEEK_API_KEY` 环境变量里（直连模式才需要）。

`galleryManifest` 指向展厅的 `manifest.json` 时，每次生成会按 `id`（文件名 slug）幂等
upsert 一条 `{id,title,category,formula,challenge,file}`，新条目排在最前，写失败只告警、
不影响实验落盘。`file` 自动写成相对 manifest 的路径（如 `./labs/xxx.html`），
所以 `outputDir` 一般指向 `gallery/labs`。

## 自测（探针）

`probe.mjs` 不安装进 dsh 也能验证插件是否符合真实契约：

```bash
# 在有 @deepseek-ai/* 的环境里执行（dsh profile，或把 node_modules 指到 dsh 安装目录）
node probe.mjs
```

它用 dsh 自己的 `defineTool` 编译 schema、用 `validateJsonSchemaValue` 校验返回值，覆盖：
导出契约、`ctx.tools` 注册、参数必填校验、两个工具的 execute 端到端、无后端无 Key 的失败路径。

最近一次结果：**24 / 24 通过**。

## 目录

```
dsh-plugin-scicanvas/
├── index.js            插件主体（ESM，无构建步骤）
├── package.json        dsh.bundle.patch 声明 + exports
├── cordis.patch.yml    插件行与配置
├── locale/{en,zh}.json 插件列表里的标题/描述
├── icon.svg            插件图标
├── probe.mjs           契约自测
└── README.md
```

> 0.2.0 起移除了 TypeScript 构建链（`tsc` + `lib/`）：Host bundle 不需要编译，直接跑 `index.js`，
> 也就没有 `cordis` 依赖版本那些坑了。