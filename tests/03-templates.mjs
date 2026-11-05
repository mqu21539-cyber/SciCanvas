/**
 * 03 · 模板渲染 + 真实浏览器验证
 *
 * 步骤：用 B 的 generator 渲染全部模板 → 逐个用 Chrome 打开 →
 *       断言无 JS 异常、canvas 真的画了像素、滑块注入成功。
 */
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { suite, skipped } from './lib/assert.mjs'
import { findChrome, sleep, withChrome } from './lib/browser.mjs'

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'))
const ROOT = path.resolve(HERE, '..')
const GEN_DIR = path.join(ROOT, 'B-模板化生成')
const OUT = path.join(GEN_DIR, 'out')

if (!findChrome()) process.exit(skipped('未找到 Chrome/Edge（可设 CHROME_PATH）'))

const PY =
  process.env.SCICANVAS_PYTHON ||
  path.join(ROOT, 'A-自由生成', 'backend', '.venv', 'Scripts', 'python.exe')
const python = fs.existsSync(PY) ? PY : 'python'

const res = spawnSync(python, ['generator.py', '--list'], { cwd: GEN_DIR, encoding: 'utf-8' })
if (res.status !== 0) process.exit(skipped(`generator 无法运行（${python}）：${(res.stderr || '').slice(0, 80)}`))

const names = [...res.stdout.matchAll(/^\[(\w+)\]/gm)].map((m) => m[1])
const t = suite('03 · 模板渲染与浏览器验证')
if (!t.ok('至少 10 个模板', names.length >= 10, names.join(', '))) process.exit(t.done())

fs.mkdirSync(OUT, { recursive: true })
for (const name of names) {
  const r = spawnSync(python, ['generator.py', '--template', name, '--out', path.join(OUT, `${name}.html`)], {
    cwd: GEN_DIR,
    encoding: 'utf-8',
  })
  if (r.status !== 0) t.ok(`${name} 渲染`, false, (r.stderr || '').slice(0, 80))
}

await withChrome(async ({ newPage }) => {
  for (const name of names) {
    const file = path.join(OUT, `${name}.html`)
    if (!fs.existsSync(file)) continue
    const cdp = await newPage(`file:///${file.replace(/\\/g, '/')}`)

    // 等页面真正就绪再断言：新建标签后立刻取值会撞上导航竞态
    let ready = false
    for (let i = 0; i < 25; i++) {
      await sleep(200)
      ready = await cdp.eval(`document.readyState === 'complete' && !!document.querySelector('canvas')`)
      if (ready) break
    }
    await sleep(600) // 让 rAF 至少画几帧
    if (!ready) {
      t.ok(`${name}: 页面就绪`, false, '2.5s 内未出现 canvas')
      continue
    }

    const info = await cdp.eval(`(() => {
      const c = document.querySelector('canvas');
      if (!c) return { canvas: false };
      let painted = 0, sampled = 0;
      try {
        const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        for (let i = 3; i < d.length; i += 4 * 997) { sampled++; if (d[i] > 0) painted++; }
      } catch (e) { return { canvas: true, err: String(e) }; }
      return { canvas: true, painted, sampled, sliders: document.querySelectorAll('input[type=range]').length };
    })()`)

    const errs = cdp.errors()
    t.ok(`${name}: 无 JS 异常`, errs.length === 0, errs.slice(0, 1).join(' | '))
    t.ok(`${name}: canvas 已绘制`, (info.painted || 0) > 0, `${info.painted || 0}/${info.sampled || 0}`)
    t.ok(`${name}: 滑块注入`, (info.sliders || 0) >= 2, String(info.sliders))
  }
})

process.exit(t.done())