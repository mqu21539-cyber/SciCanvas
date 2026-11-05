/**
 * dsh-plugin-scicanvas —— DeepSeek Harness 插件（Host bundle）
 *
 * 依据：dsh 内置技能 cordis-plugin-development 的 host-plugin.md
 *   - 插件是 bundle：package.json 声明 dsh.bundle.patch，patch 插入行
 *   - Host 导出形式：export function apply(ctx, config) + export const inject
 *   - 工具注册：inject 里声明 'tools'，然后在 apply 内 ctx.tools.register(defineTool({...}))
 *
 * 注意（与早期文档的差异）：
 *   - 服务名是 tools（复数），不是 tool；
 *   - 定义工具必须用 @deepseek-ai/dsh-tools 的 defineTool()；
 *   - parameters 是"字段表"（每字段自带 required: true），不是 JSON Schema 的 properties/required 数组；
 *   - object 类型必须显式声明 additionalProperties。
 */
import * as fs from 'node:fs'
import * as path from 'node:path'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'scicanvas'
export const inject = ['tools']

/** 生成一次实验大约 25–30s，给足工具超时（默认超时会掐断）。 */
const GENERATE_TIMEOUT_MS = 240_000

const FALLBACK_SYSTEM_PROMPT = `
你是一位精通 HTML5 Canvas、SVG 与 Tailwind CSS 的计算物理与交互视觉架构师。
请将用户输入的科学概念转化为一个【完全自包含的单文件 HTML】2D 交互式仿真实验室。
要求：
1. 单文件内包含所有 HTML/CSS/JS，通过 CDN 引入 Tailwind CSS (https://cdn.tailwindcss.com)。
2. 采用深色科技风 (bg-slate-950 text-slate-100)，包含高帧率 requestAnimationFrame 2D 动态画布、2-3个参数调节滑块、暂停/重置按钮，以及一条"直觉反差挑战题"。
3. 只输出完整的 <!DOCTYPE html>...</html> 代码，禁止包含解释性文字。
`

/** 清理模型输出中可能包裹的 Markdown 代码块标记 */
function extractHtml(raw) {
  const match = String(raw || '').match(/```(?:html)?\s*(<!DOCTYPE html>[\s\S]*?<\/html>)\s*```/i)
  return match ? match[1].trim() : String(raw || '').trim()
}

/**
 * 把新实验登记进展厅 manifest.json（按 id 幂等覆盖，新条目排在最前）。
 * 写入失败只告警，不影响实验本身落盘。
 * @param {string} manifestPath 绝对路径
 * @param {{id:string,title:string,category:string,formula:string,challenge:string,file:string}} entry
 * @param {{warn?: (msg: string) => void}} [logger]
 * @returns {boolean} 是否写入成功
 */
function upsertGalleryEntry(manifestPath, entry, logger) {
  try {
    fs.mkdirSync(path.dirname(manifestPath), { recursive: true })
    let entries = []
    if (fs.existsSync(manifestPath)) {
      try {
        const parsed = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'))
        if (Array.isArray(parsed)) entries = parsed
      } catch (e) {
        logger?.warn?.(`[scicanvas] manifest 解析失败，将按单条重建：${e.message}`)
      }
    }
    const next = [entry, ...entries.filter((item) => item && item.id !== entry.id)]
    const tmp = `${manifestPath}.tmp`
    fs.writeFileSync(tmp, `${JSON.stringify(next, null, 2)}\n`, 'utf-8')
    fs.renameSync(tmp, manifestPath)
    return true
  } catch (e) {
    logger?.warn?.(`[scicanvas] 写入 gallery manifest 失败：${e.message}`)
    return false
  }
}

/** 本地时间戳，用作中文标题无法 slug 化时的兜底文件名：lab-20261105-112233 */
function localStamp() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `lab-${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
}

/** 跨平台在默认浏览器中打开生成的 HTML 实验文件 */
async function openFileInBrowser(filePath) {
  const { spawn } = await import('node:child_process')
  const platform = process.platform
  const [cmd, args] =
    platform === 'win32'
      ? ['cmd', ['/c', 'start', '', filePath]]
      : platform === 'darwin'
        ? ['open', [filePath]]
        : ['xdg-open', [filePath]]
  try {
    spawn(cmd, args, { detached: true, stdio: 'ignore' }).unref()
  } catch {
    /* 打不开浏览器不算失败，文件已经落盘 */
  }
}

export function apply(ctx, config = {}) {
  const backendUrl = config.backendUrl || 'http://127.0.0.1:8010'
  const apiKey = config.deepseekApiKey || process.env.DEEPSEEK_API_KEY || ''
  const baseUrl = config.deepseekBaseUrl || process.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com'
  const outputDir = path.resolve(process.cwd(), config.outputDir || './scicanvas-labs')
  const autoOpen = config.autoOpenBrowser ?? true
  /** 展厅清单：给了路径才登记，缺省不影响既有行为。 */
  const galleryManifest = config.galleryManifest
    ? path.resolve(process.cwd(), config.galleryManifest)
    : null
  const galleryCategory = config.galleryCategory || 'AI 实时生成'

  fs.mkdirSync(outputDir, { recursive: true })

  /**
   * 双模生成：优先本地 FastAPI 双 Agent；未启动则直连 DeepSeek。
   */
  async function generateLabHtml(conceptPrompt) {
    try {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), 2500)
      const health = await fetch(`${backendUrl}/api/health`, { signal: controller.signal })
      clearTimeout(timer)
      if (health.ok) {
        const res = await fetch(`${backendUrl}/api/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: conceptPrompt }),
        })
        if (res.ok) {
          const data = await res.json()
          return {
            title: data?.plan?.title || 'scicanvas-experiment',
            html: data.html,
            plan: data.plan,
            mode: 'fastapi-dual-agent',
          }
        }
      }
    } catch {
      /* 后端没起来，走内置直连 */
    }

    if (!apiKey) {
      throw new Error(
        `未检测到 ${backendUrl} 上的 SciCanvas 后端，且未配置 DEEPSEEK_API_KEY（可在插件 config 或环境变量里给）。`
      )
    }

    const res = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: 'deepseek-chat',
        temperature: 0.2,
        messages: [
          { role: 'system', content: FALLBACK_SYSTEM_PROMPT },
          { role: 'user', content: `请为以下科学概念或论文摘要生成单文件交互式 2D 仿真实验室 HTML：\n${conceptPrompt}` },
        ],
      }),
    })
    if (!res.ok) {
      throw new Error(`DeepSeek 调用失败 (${res.status}): ${(await res.text()).slice(0, 300)}`)
    }
    const json = await res.json()
    const raw = json?.choices?.[0]?.message?.content || ''
    return { title: `lab-${Date.now()}`, html: extractHtml(raw), plan: null, mode: 'standalone-direct' }
  }

  ctx.tools.register(
    defineTool({
      name: 'render_science_lab',
      description:
        '把物理、数学、生物或经济学等抽象概念、公式或论文段落，实时转成可拖拽滑块的 2D 交互式 HTML5 Canvas/SVG 实验沙盒，并在浏览器打开。用户想「看演示」「可视化」「互动模拟」某个科学概念时调用。',
      timeoutMs: GENERATE_TIMEOUT_MS,
      parameters: {
        concept_prompt: {
          type: 'string',
          required: true,
          description: '要可视化的科学概念、定律描述或论文摘要，越具体越好（含想调的参数）。',
        },
        filename: {
          type: 'string',
          description: '保存用的英文文件名（不含扩展名），如 doppler-effect。省略则按标题生成。',
        },
      },
      output: {
        schema: {
          type: 'object',
          additionalProperties: false,
          properties: {
            status: { type: 'string', required: true },
            engine_mode: { type: 'string', required: true },
            saved_file: { type: 'string', required: true },
            intuition_challenge: { type: 'string', required: true },
            message: { type: 'string', required: true },
          },
        },
        render: (_args, value) => [{ type: 'text', text: value.message }],
      },
      presentCall: (args) => ({
        card: 'generic',
        title: '生成 2D 互动实验室',
        kind: 'other',
        rawInput: args.concept_prompt,
      }),
      async execute(args) {
        const result = await generateLabHtml(args.concept_prompt)
        // 纯中文标题 slug 化后会变成空串，若不兜底，所有实验都会覆盖同一个 scicanvas-lab.html
        const slug = String(args.filename || result.title || '')
          .toLowerCase()
          .replace(/[^a-z0-9-_]+/g, '-')
          .replace(/^-+|-+$/g, '')
          .slice(0, 60)
        const safeName = slug || localStamp()
        const filePath = path.join(outputDir, `${safeName}.html`)
        fs.writeFileSync(filePath, result.html, 'utf-8')
        if (galleryManifest) {
          upsertGalleryEntry(
            galleryManifest,
            {
              id: safeName,
              title: result.title || safeName,
              category: galleryCategory,
              formula: result?.plan?.formula_latex || '',
              challenge: result?.plan?.intuition_challenge || '',
              file: `./${path
                .relative(path.dirname(galleryManifest), filePath)
                .split(path.sep)
                .join('/')}`,
            },
            ctx.logger
          )
        }
        if (autoOpen) await openFileInBrowser(filePath)
        return {
          status: 'success',
          engine_mode: result.mode,
          saved_file: filePath,
          intuition_challenge:
            result?.plan?.intuition_challenge || '拖动界面里的参数滑块，观察临界状态下的物理量突变。',
          message: `已生成交互式 2D 实验室并保存到 ${filePath}（${result.mode}，已尝试在浏览器打开）。`,
        }
      },
    })
  )

  ctx.tools.register(
    defineTool({
      name: 'heal_science_lab',
      description:
        '当已生成的 SciCanvas 实验室 HTML 出现运行时报错或渲染异常时，把错误信息交给修复 Agent，就地修好该文件。',
      timeoutMs: GENERATE_TIMEOUT_MS,
      parameters: {
        file_path: { type: 'string', required: true, description: '报错的 HTML 文件绝对路径' },
        error_message: { type: 'string', required: true, description: '浏览器控制台报错或异常描述' },
      },
      output: {
        schema: {
          type: 'object',
          additionalProperties: false,
          properties: {
            status: { type: 'string', required: true },
            file_path: { type: 'string', required: true },
            message: { type: 'string', required: true },
          },
        },
        render: (_args, value) => [{ type: 'text', text: value.message }],
      },
      async execute(args) {
        if (!fs.existsSync(args.file_path)) {
          throw new Error(`文件不存在：${args.file_path}`)
        }
        const broken = fs.readFileSync(args.file_path, 'utf-8')
        let res
        try {
          res = await fetch(`${backendUrl}/api/fix`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ html: broken, error: args.error_message }),
          })
        } catch {
          throw new Error(`自愈需要一个运行在 ${backendUrl} 的 FastAPI 后端（本工具没有内置降级模式）。`)
        }
        if (!res.ok) throw new Error(`自愈接口返回异常：${res.status}`)
        const data = await res.json()
        fs.writeFileSync(args.file_path, data.html, 'utf-8')
        if (autoOpen) await openFileInBrowser(args.file_path)
        return {
          status: 'healed',
          file_path: args.file_path,
          message: `已修复并覆盖 ${args.file_path}（已尝试重新在浏览器打开）。`,
        }
      },
    })
  )

  return () => {
    ctx.logger?.info?.('[dsh-plugin-scicanvas] 已卸载')
  }
}