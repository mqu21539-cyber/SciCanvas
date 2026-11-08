# GitHub 发布手册

> 这份手册里的每一步都只差"在浏览器里点一下"，命令部分是复制即用。
> 仓库当前状态：分支 `master` · 34 次提交 · 追踪文件 100 个 · `.git` 12.4 MB。

---

## 0. 发布前自查（已完成，可跳过）

| 检查项 | 结果 |
| :--- | :--- |
| git 身份 | `WenquanMa <mqu21539@gmail.com>` ✅ |
| `.env` / 密钥是否进过历史 | **0 条** ✅ |
| 工作区是否有 API Key 残留 | **0 处** ✅ |
| 最大文件 | `assets/demo.gif` 3.13 MB（低于 GitHub 100 MB 单文件上限）✅ |
| Pages workflow | `.github/workflows/deploy-pages.yml` 已就绪 ✅ |

> ⚠️ `master` 与 workflow 里的 `branches: ["main"]` **不一致**。
> 要么把仓库默认分支设成 `main`（推荐，见第 2 步），要么改 workflow。
> 下面按"改成 main"写。

---

## 1. 建仓库

GitHub 右上角 **+ → New repository**：

| 字段 | 填什么 |
| :--- | :--- |
| Repository name | `SciCanvas` |
| Description | `Turn any textbook concept or arXiv paper into an interactive 2D lab in ~17s. Dual-agent + 10 parameterized templates, self-healing sandbox, DeepSeek Harness plugin.` |
| 可见性 | Public |
| Initialize | **什么都不要勾**（不要 README / .gitignore / license，本地都有了） |

---

## 2. 本地推上去

```bash
cd D:\SciCanvas

# 把 master 改成 main（与 workflow 对齐）
git branch -m master main

# 换成你的用户名
git remote add origin https://github.com/<你的用户名>/SciCanvas.git

git push -u origin main
```

推之前如果想先确认没把大文件带上：

```bash
git count-objects -vH
```

---

## 3. 仓库设置（网页操作，4 处）

### 3.1 About 区（右侧齿轮 ⚙️）

```
Description:
Turn any textbook concept or arXiv paper into an interactive 2D lab in ~17s.
Dual-agent + 10 parameterized templates, self-healing sandbox, DeepSeek Harness plugin.

Website:
https://<你的用户名>.github.io/SciCanvas/
```

**Topics**（一行一个，粘进去回车）：

```
deepseek
deepseek-harness
dsh
cordis-plugin
generative-ui
ai-agents
science-visualization
physics-simulation
nextjs
fastapi
education
```

### 3.2 Social preview

**Settings → General → Social preview → Upload image**

上传 `assets/social-preview.png`（1280×640 已做好）。

### 3.3 Pages

**Settings → Pages → Build and deployment → Source = GitHub Actions**

不需要选分支，workflow 已经写好了。推完第一次后，
Actions 里会出现 `Deploy SciCanvas Live Gallery to GitHub Pages`，
跑完就能访问 `https://<用户名>.github.io/SciCanvas/`。

> 展厅是纯静态的，`gallery/index.html` + 5 个实验，不需要后端。

### 3.4 分支保护（可选）

如果想让 `main` 保持绿：

**Settings → Branches → Add branch protection rule**
- Branch name pattern: `main`
- 勾 `Require status checks to pass`（如果以后加 CI）

---

## 4. 打第一个 Release（可选但推荐）

```bash
git tag -a v1.4.0 -m "SciCanvas v1.4.0 — holographic 2.5D shell, 10 templates, direct manipulation"
git push origin v1.4.0
```

然后 **Releases → Draft a new release → 选 v1.4.0**，
把 `CHANGELOG.md` 里 v1.0.0 之后的内容粘进去当说明。

---

## 5. 宣发文案（直接复制）

**一句话简介**

> 贴一段课本原文或 arXiv 编号，17 秒后得到一个能拖滑块、能直接抓画布物体的 2D 交互实验。
> 两条路径：模板命中 1.5 秒，没命中就双 Agent 现场写。

**Show HN**

```
Show HN: SciCanvas – Turn textbook concepts and papers into interactive 2D labs

I got tired of explaining physics with static LaTeX, so I built a tool that turns
a paragraph or an arXiv link into a playable single-file HTML lab.

How it works: a router first checks 10 parameterized templates (1.5s, physics is
guaranteed correct). If nothing matches, a planner+coder pair writes ~50 lines of
JS that runs inside a fixed holographic shell (4 SVG layers, oscilloscope, filters).

Two things I'm proud of:
- Self-healing: if the generated lab throws at runtime, the error is posted back,
  the backend rewrites only the offending JS block (never the whole file), and it re-renders.
- Direct manipulation: you can drag the object in the canvas instead of finding the slider.

MIT, single-file output, works offline. Feedback welcome on the physics correctness.
```

**小红书 / B站 / 知乎**

> 用 AI 把课本变成能玩的实验：[贴 GIF]
> 输入「单摆阻尼振动」，17 秒出四层全息沙盒——示波器、子弹时间、蓝图滤镜、还能直接拖画布里的摆球改参数。
> 常见概念走模板只要 1.5 秒。开源。

---

## 6. 推完之后

- [ ] Actions 里 Pages 部署是否绿
- [ ] 打开 `https://<用户名>.github.io/SciCanvas/`，5 个实验能跑
- [ ] README 顶部的 GIF 能加载（GitHub 会缓存 raw，可能需要等几分钟）
- [ ] 仓库首页右侧 Topics 显示正常

---

*最后更新：2026-11-08*