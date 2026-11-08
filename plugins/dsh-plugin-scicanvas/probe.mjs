/**
 * 插件探针 / 自测：不安装到 dsh，也能验证插件定义是否符合 dsh 真实契约。
 * 关键点：用 dsh 自己的 validateJsonSchemaValue 校验工具返回值，
 *        用 dsh 自己的 defineTool 编译 parameters/output schema。
 */
import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'
import { validateJsonSchemaValue } from '@deepseek-ai/dsh-tools'

const PLUGIN = new URL('./index.js', import.meta.url)
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'scicanvas-probe-'))
let pass = 0
let fail = 0

function ok(label, cond, extra = '') {
  if (cond) {
    pass++
    console.log(`  PASS  ${label}${extra ? '  [' + extra + ']' : ''}`)
  } else {
    fail++
    console.log(`  FAIL  ${label}${extra ? '  [' + extra + ']' : ''}`)
  }
}

const plugin = await import(PLUGIN.href)

console.log('=== 1. 导出契约 ===')
ok("export name 是字符串", typeof plugin.name === 'string', plugin.name)
ok("inject 声明了 'tools'", Array.isArray(plugin.inject) && plugin.inject.includes('tools'),
   JSON.stringify(plugin.inject))
ok('export apply 是函数', typeof plugin.apply === 'function')

console.log('\n=== 2. 注册到 ctx.tools ===')
const registered = []
let disposed = false
const ctx = {
  tools: { register(tool) { registered.push(tool); return () => { disposed = true } } },
  logger: { info() {} },
}
const cleanup = plugin.apply(ctx, {
  backendUrl: 'http://127.0.0.1:9',
  deepseekApiKey: '',
  outputDir: tmp,
  autoOpenBrowser: false,
})
ok('注册了 2 个工具', registered.length === 2, registered.map((t) => t.name).join(', '))
ok('apply 返回清理函数', typeof cleanup === 'function')

const render = registered.find((t) => t.name === 'render_science_lab')
const heal = registered.find((t) => t.name === 'heal_science_lab')
ok('render_science_lab 存在', Boolean(render))
ok('heal_science_lab 存在', Boolean(heal))

console.log('\n=== 3. 工具定义符合 dsh 契约 ===')
for (const t of registered) {
  ok(`${t.name}: parameters 被编译成 object schema`, t.parameters?.type === 'object')
  ok(`${t.name}: 参数 required 正确`, Array.isArray(t.parameters?.required),
     JSON.stringify(t.parameters?.required))
  ok(`${t.name}: output.schema 存在`, Boolean(t.output?.schema))
  ok(`${t.name}: execute 是函数`, typeof t.execute === 'function')
}
ok('render 的 concept_prompt 必填', (render.parameters.required || []).includes('concept_prompt'))

console.log('\n=== 4. 参数校验走 dsh 真校验器 ===')
const badArgs = validateJsonSchemaValue(render.parameters, {}, '')
ok('缺必填参数会被拒', badArgs.length > 0, JSON.stringify(badArgs))
const goodArgs = validateJsonSchemaValue(render.parameters, { concept_prompt: '傅里叶变换' }, '')
ok('合法参数通过', goodArgs.length === 0)

console.log('\n=== 5. execute 端到端（模拟后端）===')
const HTML = '<!DOCTYPE html><html><body><canvas></canvas></body></html>'
globalThis.fetch = async (url) => {
  const u = String(url)
  if (u.endsWith('/api/health')) return { ok: true, status: 200 }
  if (u.endsWith('/api/generate')) {
    return {
      ok: true,
      status: 200,
      json: async () => ({ plan: { title: '傅里叶合成方波', intuition_challenge: '圆越多会怎样？' }, html: HTML }),
    }
  }
  return { ok: false, status: 404, text: async () => 'nope', json: async () => ({}) }
}

const out = await render.execute({ concept_prompt: '傅里叶级数', filename: 'fourier' })
const file = path.join(tmp, 'fourier.html')
ok('文件已落盘', fs.existsSync(file), file)
ok('文件内容正确', fs.existsSync(file) && fs.readFileSync(file, 'utf-8') === HTML)
ok('返回值通过 output schema 校验',
   validateJsonSchemaValue(render.output.schema, out, '').length === 0,
   JSON.stringify(out).slice(0, 90))

console.log('\n=== 6. heal 工具 ===')
fs.writeFileSync(path.join(tmp, 'broken.html'), '<html>broken</html>', 'utf-8')
globalThis.fetch = async (url) => {
  if (String(url).endsWith('/api/fix')) {
    return { ok: true, status: 200, json: async () => ({ html: '<!DOCTYPE html><html><body>fixed</body></html>' }) }
  }
  return { ok: false, status: 404, text: async () => '' }
}
const healed = await heal.execute({ file_path: path.join(tmp, 'broken.html'), error_message: 'ReferenceError: x' })
ok('修复后文件已覆盖', fs.readFileSync(path.join(tmp, 'broken.html'), 'utf-8').includes('fixed'))
ok('heal 返回值合法', validateJsonSchemaValue(heal.output.schema, healed, '').length === 0)

console.log('\n=== 7. 失败路径 ===')
globalThis.fetch = async () => { throw new Error('ECONNREFUSED') }
let msg = ''
try {
  await render.execute({ concept_prompt: 'x' })
} catch (e) {
  msg = String(e.message)
}
ok('无后端且无 Key 时给出可读错误', msg.includes('DEEPSEEK_API_KEY'), msg.slice(0, 60))

console.log(`\n结果：通过 ${pass} / 失败 ${fail}`)
process.exit(fail === 0 ? 0 : 1)