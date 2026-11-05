// NOTE: Cordis 的工具注册入口请以你本机 dsh 版本为准，见 docs/技术可行性评估.md
import type { Context } from 'cordis'
import * as fs from 'fs'
import * as path from 'path'
import { exec } from 'child_process'
export interface Config {
  /** SciCanvas FastAPI 后端地址（默认连接本地 8000 端口） */
  backendUrl?: string
  /** 当未启动 Python 后端时，插件可直接调用的 DeepSeek API Key */
  deepseekApiKey?: string
  /** DeepSeek API 基础地址 */
  deepseekBaseUrl?: string
  /** 生成的独立 HTML 实验室保存目录 */
  outputDir?: string
  /** 生成完成后是否自动在系统浏览器中打开交互沙盒 */
  autoOpenBrowser?: boolean
}
export const name = 'scicanvas'
const FALLBACK_SYSTEM_PROMPT = `
你是一位精通 HTML5 Canvas、SVG 与 Tailwind CSS 的计算物理与交互视觉架构师。
请将用户输入的科学概念转化为一个【完全自包含的单文件 HTML】2D 交互式仿真实验室。
要求：
1. 单文件内包含所有 HTML/CSS/JS，通过 CDN 引入 Tailwind CSS (https://cdn.tailwindcss.com)。
2. 采用深色科技风 (bg-slate-950 text-slate-100)，包含高帧率 requestAnimationFrame 2D 动态画布、2-3个参数调节滑块、暂停/重置按钮，以及一条“直觉反差挑战题”。
3. 只输出完整的 <!DOCTYPE html>...</html> 代码，禁止包含解释性文字。
`
/**
 * 清理模型输出中可能包裹的 Markdown 代码块标记
 */
function extractHtml(raw: string): string {
  const match = raw.match(/```(?:html)?\s*(<!DOCTYPE html>[\s\S]*?<\/html>)\s*```/i)
  return match ? match[1].trim() : raw.trim()
}
/**
 * 跨平台在默认浏览器中打开生成的 HTML 实验文件
 */
function openFileInBrowser(filePath: string) {
  const platform = process.platform
  const cmd =
    platform === 'win32'
      ? `start "" "${filePath}"`
      : platform === 'darwin'
      ? `open "${filePath}"`
      : `xdg-open "${filePath}"`
  exec(cmd)
}
export function apply(ctx: Context, config: Config = {}) {
  const backendUrl = config.backendUrl || 'http://127.0.0.1:8000'
  const apiKey = config.deepseekApiKey || process.env.DEEPSEEK_API_KEY || ''
  const baseUrl = config.deepseekBaseUrl || process.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com'
  const outputDir = path.resolve(process.cwd(), config.outputDir || './scicanvas-labs')
  const autoOpen = config.autoOpenBrowser ?? true
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true })
  }
  /**
   * 核心生成函数：优先请求本地 FastAPI 双 Agent 引擎；若未启动则自动切换为内置直连模式
   */
  async function generateLabHtml(conceptPrompt: string): Promise<{
    title: string
    html: string
    plan?: Record<string, any>
    mode: 'fastapi-dual-agent' | 'standalone-direct'
  }> {
    // 1. 尝试调用本地 FastAPI 双 Agent 后端
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 2500)
      const healthCheck = await fetch(`${backendUrl}/api/health`, { signal: controller.signal })
      clearTimeout(timeout)
      if (healthCheck.ok) {
        const res = await fetch(`${backendUrl}/api/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: conceptPrompt }),
        })
        if (res.ok) {
          const data = (await res.json()) as { plan: any; html: string }
          return {
            title: data.plan?.title || 'scicanvas-experiment',
            html: data.html,
            plan: data.plan,
            mode: 'fastapi-dual-agent',
          }
        }
      }
    } catch {
      // 本地 FastAPI 未启动，平滑降级到插件内置直连模式
    }
    // 2. 内置直连 DeepSeek API 模式（零后端依赖）
    if (!apiKey) {
      throw new Error(
        '未检测到运行中的 SciCanvas FastAPI 后端，且未配置 DEEPSEEK_API_KEY。请在环境变量或 cordis.yml 中配置密钥。'
      )
    }
    const res = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'deepseek-chat',
        temperature: 0.2,
        messages: [
          { role: 'system', content: FALLBACK_SYSTEM_PROMPT },
          {
            role: 'user',
            content: `请为以下科学概念或论文摘要生成单文件交互式 2D 仿真实验室 HTML：\n${conceptPrompt}`,
          },
        ],
      }),
    })
    if (!res.ok) {
      const errText = await res.text()
      throw new Error(`DeepSeek API 调用失败 (${res.status}): ${errText}`)
    }
    const json = (await res.json()) as any
    const rawContent = json.choices?.[0]?.message?.content || ''
    return {
      title: `lab-${Date.now()}`,
      html: extractHtml(rawContent),
      mode: 'standalone-direct',
    }
  }
  // Tool 1: 生成 2D 互动科学实验室
  const renderToolSpec = {
    name: 'render_science_lab',
    description:
      '将物理、数学、计算机、生物或经济学等抽象概念、公式或论文段落，实时转化为可拖拽滑块的 2D 动态交互式 HTML5 Canvas/SVG 实验沙盒。当用户需要直观演示、科学可视化或互动模拟时调用此工具。',
    parameters: {
      type: 'object',
      properties: {
        concept_prompt: {
          type: 'string',
          description: '需要可视化的科学概念、物理定律描述或论文摘要，越具体越好。',
        },
        filename: {
          type: 'string',
          description: '保存的英文文件名标识（不含扩展名），例如 doppler-effect 或 gradient-descent',
        },
      },
      required: ['concept_prompt'],
    },
    execute: async (args: { concept_prompt: string; filename?: string }) => {
      const result = await generateLabHtml(args.concept_prompt)
      const safeName = (args.filename || result.title || 'scicanvas-lab')
        .toLowerCase()
        .replace(/[^a-z0-9-_]/g, '-')
      const filePath = path.join(outputDir, `${safeName}.html`)
      fs.writeFileSync(filePath, result.html, 'utf-8')
      if (autoOpen) {
        openFileInBrowser(filePath)
      }
      return {
        status: 'success',
        engine_mode: result.mode,
        saved_file: filePath,
        intuition_challenge:
          result.plan?.intuition_challenge ||
          '拖动界面中的参数滑块，观察临界状态下的物理轨迹与数值突变！',
        message: `已成功生成交互式 2D 实验室并保存至 ${filePath}（已自动在浏览器打开沙盒预览）。`,
      }
    },
  }
  // Tool 2: 自愈修复报错的实验代码
  const healToolSpec = {
    name: 'heal_science_lab',
    description: '当生成的 SciCanvas 实验室 HTML 出现渲染异常或控制台报错时，自动修复对应的单文件 HTML 代码。',
    parameters: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: '报错的 HTML 文件路径',
        },
        error_message: {
          type: 'string',
          description: '浏览器控制台抛出的错误信息或界面异常描述',
        },
      },
      required: ['file_path', 'error_message'],
    },
    execute: async (args: { file_path: string; error_message: string }) => {
      const brokenHtml = fs.readFileSync(args.file_path, 'utf-8')
      let res: Response
      try {
        res = await fetch(`${backendUrl}/api/fix`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ html: brokenHtml, error: args.error_message }),
        })
      } catch {
        throw new Error(`自愈需要一个在 ${backendUrl} 运行的 FastAPI 后端（本工具暂无内置降级模式）。`)
      }
      if (!res.ok) {
        throw new Error(`自愈接口返回异常: ${res.status}`)
      }
      const data = (await res.json()) as { html: string }
      fs.writeFileSync(args.file_path, data.html, 'utf-8')
      if (autoOpen) {
        openFileInBrowser(args.file_path)
      }
      return {
        status: 'healed',
        file_path: args.file_path,
        message: '已完成沙盒代码热修复并重新打开预览！',
      }
    },
  }
  // 兼容挂载到 DeepSeek Harness 的工具上下文与全局服务中。
  // 注意：下面两个入口名来自社区文档的推测，不同 dsh 版本可能完全不同。
  // 找不到入口时必须显式失败——「装上了但没有工具」比直接报错更难排查。
  const anyCtx = ctx as any
  let registered = false
  if (typeof anyCtx.tool?.register === 'function') {
    anyCtx.tool.register(renderToolSpec)
    anyCtx.tool.register(healToolSpec)
    registered = true
  } else if (typeof anyCtx.agent?.registerTool === 'function') {
    anyCtx.agent.registerTool(renderToolSpec)
    anyCtx.agent.registerTool(healToolSpec)
    registered = true
  }
  if (!registered) {
    throw new Error(
      '[dsh-plugin-scicanvas] 未找到 Cordis 工具注册入口：ctx.tool.register / ctx.agent.registerTool 均不可用。' +
        '请先在目标 dsh 版本上运行探针（apply(ctx){ console.log(Object.keys(ctx)) }），再按实际 API 对齐本文件。'
    )
  }
  // 同时暴露 ctx.scicanvas 服务供其他 Cordis 插件组合调用
  anyCtx.scicanvas = {
    generateLabHtml,
    renderToolSpec,
    healToolSpec,
  }
  console.log('✅ [dsh-plugin-scicanvas] 插件已成功挂载！保存目录:', outputDir)
}
