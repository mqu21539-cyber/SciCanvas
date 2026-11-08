/**
 * 01 · 插件契约测试
 *
 * 用 dsh 自己的 defineTool 编译 schema、用 validateJsonSchemaValue 校验返回值，
 * 因此需要能解析 @deepseek-ai/dsh-tools（在 dsh profile 里跑，或把
 * plugins/dsh-plugin-scicanvas/node_modules 指向 dsh 安装目录）。
 */
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import { suite, skipped } from './lib/assert.mjs'
import { ROOT, loadDshTools } from './lib/dsh-tools.mjs'

const PLUGIN = path.join(ROOT, 'plugins', 'dsh-plugin-scicanvas', 'index.js')

const loaded = await loadDshTools()
if (!loaded) {
  process.exit(
    skipped('未找到 @deepseek-ai/dsh-tools（可设 DSH_TOOLS_PATH，或先运行 tools/probe-dsh-asar.mjs）')
  )
}

const { validateJsonSchemaValue } = loaded.mod
const t = suite('01 · dsh 插件契约')

if (!fs.existsSync(PLUGIN)) {
  t.ok('找到插件 index.js', false, PLUGIN)
  process.exit(t.done())
}

let plugin
try {
  plugin = await import(pathToFileURL(PLUGIN).href)
} catch (e) {
  process.exit(
    skipped(
      `插件自身解析不到 @deepseek-ai/dsh-tools。在 dsh profile 内运行，或把 ` +
        `\dsh-plugin-scicanvas\\node_modules 软链到 dsh 的 node_modules。（${String(e.message).slice(0, 60)}）`
    )
  )
}

if (!t.ok('export name 是字符串', typeof plugin.name === 'string', plugin.name)) process.exit(t.done())
t.ok("inject 含 'tools'", Array.isArray(plugin.inject) && plugin.inject.includes('tools'), JSON.stringify(plugin.inject))
t.ok('export apply 是函数', typeof plugin.apply === 'function')

const registered = []
const ctx = { tools: { register: (tool) => { registered.push(tool); return () => {} } }, logger: { info() {} } }
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sc-contract-'))
const cleanup = plugin.apply(ctx, { backendUrl: 'http://127.0.0.1:9', deepseekApiKey: '', outputDir: tmp, autoOpenBrowser: false })

t.ok('注册 2 个工具', registered.length === 2, registered.map((x) => x.name).join(', '))
t.ok('apply 返回清理函数', typeof cleanup === 'function')

const render = registered.find((x) => x.name === 'render_science_lab')
const heal = registered.find((x) => x.name === 'heal_science_lab')
t.ok('render_science_lab 存在', Boolean(render))
t.ok('heal_science_lab 存在', Boolean(heal))

for (const tool of registered) {
  t.ok(`${tool.name}: parameters 编译为 object`, tool.parameters?.type === 'object')
  t.ok(`${tool.name}: output.schema 存在`, Boolean(tool.output?.schema))
  t.ok(`${tool.name}: execute 是函数`, typeof tool.execute === 'function')
}
t.ok('render 必填 concept_prompt', (render.parameters.required || []).includes('concept_prompt'))
t.ok('空参数被拒', validateJsonSchemaValue(render.parameters, {}, '').length > 0)
t.ok('合法参数通过', validateJsonSchemaValue(render.parameters, { concept_prompt: 'x' }, '').length === 0)

// execute：模拟后端
const HTML = '<!DOCTYPE html><html><body><canvas></canvas></body></html>'
const realFetch = globalThis.fetch
globalThis.fetch = async (url) => {
  const u = String(url)
  if (u.endsWith('/api/health')) return { ok: true, status: 200 }
  if (u.endsWith('/api/generate')) {
    return { ok: true, status: 200, json: async () => ({ plan: { title: 'T', intuition_challenge: 'Q' }, html: HTML }) }
  }
  return { ok: false, status: 404, text: async () => '', json: async () => ({}) }
}
const out = await render.execute({ concept_prompt: 'x', filename: 'contract-test' })
t.ok('产物落盘', fs.existsSync(path.join(tmp, 'contract-test.html')))
t.ok('返回值符合 output schema', validateJsonSchemaValue(render.output.schema, out, '').length === 0)

fs.writeFileSync(path.join(tmp, 'broken.html'), '<html>b</html>', 'utf-8')
globalThis.fetch = async (url) => {
  if (String(url).endsWith('/api/fix')) {
    return { ok: true, status: 200, json: async () => ({ html: '<!DOCTYPE html><html><body>fixed</body></html>' }) }
  }
  return { ok: false, status: 404, text: async () => '' }
}
const healed = await heal.execute({ file_path: path.join(tmp, 'broken.html'), error_message: 'ReferenceError: x' })
t.ok('heal 覆盖原文件', fs.readFileSync(path.join(tmp, 'broken.html'), 'utf-8').includes('fixed'))
t.ok('heal 返回值合法', validateJsonSchemaValue(heal.output.schema, healed, '').length === 0)

// ---- 展厅登记 + 中文标题的 slug 兜底 ----
const galleryDir = path.join(tmp, 'gallery')
const manifestPath = path.join(galleryDir, 'manifest.json')
const reg2 = []
plugin.apply(
  { tools: { register: (tool) => reg2.push(tool) }, logger: { info() {}, warn() {} } },
  {
    backendUrl: 'http://127.0.0.1:9',
    deepseekApiKey: '',
    outputDir: path.join(galleryDir, 'labs'),
    galleryManifest: manifestPath,
    galleryCategory: 'AI 实时生成',
    autoOpenBrowser: false,
  }
)
const render2 = reg2.find((x) => x.name === 'render_science_lab')

globalThis.fetch = async (url) => {
  if (String(url).endsWith('/api/health')) return { ok: true, status: 200 }
  return {
    ok: true,
    status: 200,
    json: async () => ({
      plan: {
        title: '弹簧振子简谐运动',
        formula_latex: 'T = 2π√(m/k)',
        intuition_challenge: '质量翻倍，周期变几倍？',
      },
      html: HTML,
    }),
  }
}

const readManifest = () => JSON.parse(fs.readFileSync(manifestPath, 'utf-8'))

await render2.execute({ concept_prompt: '弹簧振子' })
const entries = readManifest()
t.ok('生成后登记进 manifest', entries.length === 1, `id=${entries[0]?.id}`)
t.ok('中文标题回落到时间戳 id（不再撞车）', /^lab-\d{8}-\d{6}$/.test(entries[0]?.id || ''), entries[0]?.id)
t.ok('file 是相对 manifest 的 labs 路径', String(entries[0]?.file).startsWith('./labs/'), entries[0]?.file)
t.ok('category 生效', entries[0]?.category === 'AI 实时生成')
t.ok('formula/challenge 带上了蓝图字段', Boolean(entries[0]?.formula) && Boolean(entries[0]?.challenge))

await render2.execute({ concept_prompt: '弹簧振子', filename: 'spring-oscillator' })
await render2.execute({ concept_prompt: '弹簧振子', filename: 'spring-oscillator' })
const entries2 = readManifest()
t.ok('按 id 幂等（同名不重复）', entries2.filter((e) => e.id === 'spring-oscillator').length === 1)
t.ok('新条目排在最前', entries2[0]?.id === 'spring-oscillator', entries2.map((e) => e.id).join(','))

globalThis.fetch = async () => {
  throw new Error('ECONNREFUSED')
}
let msg = ''
try {
  await render.execute({ concept_prompt: 'x' })
} catch (e) {
  msg = String(e.message)
}
t.ok('无后端无 Key 时报错可读', msg.includes('DEEPSEEK_API_KEY'), msg.slice(0, 48))

globalThis.fetch = realFetch
process.exit(t.done())