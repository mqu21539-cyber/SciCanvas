#!/usr/bin/env node
/**
 * tools/capture-interactions.mjs
 *
 * 截「交互过程」而不是「一张静态图」，产出三组帧到 assets/_interactions/：
 *   slider-*.png    傅里叶模板：谐波项数从 1 拉到 25，方波被一点点拼出来
 *   selfheal-*.png  沙盒报错 → 自动调 /api/fix → 重渲染（真实后端，约 12 秒）
 *   split-*.png     输入概念 → 生成 → 开「同屏对比」，两块沙盒并排跑
 *
 * 只依赖 Node 内置 WebSocket + Chrome DevTools Protocol，不需要 puppeteer。
 * 之后用 python tools/build-demo-gifs.py 合成 GIF。
 *
 * 用法：node tools/capture-interactions.mjs [slider|selfheal|split]
 */
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
]
const CHROME = CHROME_CANDIDATES.find((p) => p && fs.existsSync(p))
if (!CHROME) {
  console.error('未找到 Chrome/Edge，设置 CHROME_PATH')
  process.exit(1)
}

const PORT = Number(process.env.CDP_PORT || 9421)
const ROOT = path.resolve('.')
const OUT = path.join(ROOT, 'assets', '_interactions')
const W = Number(process.env.FRAME_W || 1280)
const H = Number(process.env.FRAME_H || 780)
const APP = process.env.APP_URL || 'http://localhost:3000'

fs.mkdirSync(OUT, { recursive: true })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

class CDP {
  constructor(ws) {
    this.ws = ws
    this.seq = 0
    this.pending = new Map()
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id && this.pending.has(m.id)) {
        const p = this.pending.get(m.id)
        this.pending.delete(m.id)
        m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result)
      }
    })
  }
  send(method, params = {}) {
    const id = ++this.seq
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }
  async eval(expression) {
    const r = await this.send('Runtime.evaluate', {
      expression,
      awaitPromise: true,
      returnByValue: true,
    })
    if (r.exceptionDetails) throw new Error(`页面异常: ${JSON.stringify(r.exceptionDetails).slice(0, 200)}`)
    return r.result?.value
  }
  async shot(file) {
    const s = await this.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
    fs.writeFileSync(file, Buffer.from(s.data, 'base64'))
  }
}

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'scicanvas-gif-'))
const chrome = spawn(
  CHROME,
  [
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`,
    '--headless=new',
    '--hide-scrollbars',
    '--disable-gpu',
    '--no-first-run',
    '--disable-extensions',
    `--window-size=${W},${H}`,
    'about:blank',
  ],
  { stdio: 'ignore' }
)

async function openTab(url) {
  const tab = await (
    await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' })
  ).json()
  const ws = new WebSocket(tab.webSocketDebuggerUrl)
  await new Promise((r) => ws.addEventListener('open', r, { once: true }))
  const cdp = new CDP(ws)
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: W,
    height: H,
    deviceScaleFactor: 1,
    mobile: false,
  })
  return { cdp, tab }
}

async function closeTab(tab) {
  await fetch(`http://127.0.0.1:${PORT}/json/close/${tab.id}`)
}

// ---------------------------------------------------------------- 场景一：拖滑块
async function sceneSlider() {
  const file = path.join(ROOT, 'B-模板化生成', 'out', 'fourier.html')
  if (!fs.existsSync(file)) throw new Error('缺少 out/fourier.html，先跑 generator.py --template fourier')

  const { cdp, tab } = await openTab(pathToFileURL(file).href)
  for (let i = 0; i < 40; i++) {
    await sleep(200)
    const ok = await cdp.eval(`document.readyState === 'complete' && !!document.querySelector('canvas')`)
    if (ok) break
  }
  await sleep(800)

  const steps = [1, 2, 3, 4, 6, 8, 12, 16, 20, 25]
  let n = 0
  for (const v of steps) {
    await cdp.eval(`(() => {
      // 全息底座的滑块是 JS 动态创建的，用 data-k 定位（只有旧模板才有固定 id）
      const el = document.querySelector('#capsules input[data-k="n"]') || document.getElementById('n');
      if (!el) return;
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(el, '${v}');
      el.dispatchEvent(new Event('input', { bubbles: true }));
    })()`)
    await sleep(260)
    await cdp.shot(path.join(OUT, `slider-${String(n).padStart(2, '0')}.png`))
    n++
  }
  console.log(`  slider: ${n} 帧`)
  await closeTab(tab)
}

// ---------------------------------------------------------------- 场景二：自愈
async function sceneSelfheal() {
  const src = path.join(ROOT, 'B-模板化生成', 'out', 'oscillator.html')
  if (!fs.existsSync(src)) throw new Error('缺少 out/oscillator.html')
  // 在 </body> 前插一段定时抛错的脚本：先让实验正常画出来，600ms 后再崩，
  // 这样 GIF 里能看清「先能跑 → 报错 → 自愈 → 又能跑」的完整过程。
  const raw = fs.readFileSync(src, 'utf8')
  const html = raw.replace(
    '</body>',
    '<script>setTimeout(function(){ notDefinedYet(); }, 7000);</script>\n</body>'
  )
  if (html === raw) throw new Error('没找到 </body>，无法注入错误')

  const { cdp, tab } = await openTab(`${APP}/?seed=1`)
  for (let i = 0; i < 60; i++) {
    await sleep(250)
    const ready = await cdp.eval(`!!(document.querySelector('textarea') && document.querySelector('textarea')._valueTracker)`)
    if (ready) break
  }

  // 把坏掉的实验塞进 localStorage，刷新后页面会自动恢复并触发自愈
  await cdp.eval(`(() => {
    localStorage.setItem('scicanvas:last', JSON.stringify({
      prompt: '阻尼单摆：演示自愈链路',
      plan: {
        title: '阻尼单摆（自愈演示）',
        subtitle: '注入一个 ReferenceError，看沙盒自己爬起来',
        formula_latex: "θ'' = -(g/L)sinθ - cθ'",
        intuition_challenge: '阻尼越大，周期会变长吗？',
      },
      html: ${JSON.stringify(html)},
      engine: { mode: 'template', template: 'oscillator', ms: 1500, cached: true },
    }));
  })()`)
  await cdp.send('Page.reload')
  await sleep(3500)

  let n = 0
  // 先截"正常运行"的几帧（错误被延后到 7 秒才触发）
  for (let i = 0; i < 3; i++) {
    await cdp.shot(path.join(OUT, `selfheal-${String(n).padStart(2, '0')}.png`))
    n++
    await sleep(450)
  }
  // 等"修复中"横幅出现，并一直截到它消失
  for (let i = 0; i < 30; i++) {
    await sleep(700)
    const fixing = await cdp.eval(`document.body.innerText.includes('修复')`)
    await cdp.shot(path.join(OUT, `selfheal-${String(n).padStart(2, '0')}.png`))
    n++
    if (!fixing && i > 6) break
  }
  // 修好之后的稳定画面
  await sleep(800)
  for (let i = 0; i < 2; i++) {
    await cdp.shot(path.join(OUT, `selfheal-${String(n).padStart(2, '0')}.png`))
    n++
    await sleep(600)
  }
  console.log(`  selfheal: ${n} 帧`)
  await closeTab(tab)
}

// ---------------------------------------------------------------- 场景三：同屏对比
async function sceneSplit() {
  const { cdp, tab } = await openTab(APP)
  for (let i = 0; i < 60; i++) {
    await sleep(250)
    const ready = await cdp.eval(`!!(document.querySelector('textarea') && document.querySelector('textarea')._valueTracker)`)
    if (ready) break
  }

  await cdp.eval(`(() => {
    const ta = document.querySelector('textarea');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(ta, '演示单摆的阻尼振动：可调摆长、阻尼系数和重力加速度');
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  })()`)
  let n = 0
  await cdp.shot(path.join(OUT, `split-${String(n).padStart(2, '0')}.png`))
  n++

  // 点生成（命中缓存，1 秒内出结果）
  await cdp.eval(`[...document.querySelectorAll('button')].find((b) => b.textContent.includes('立即生成'))?.click()`)
  for (let i = 0; i < 30; i++) {
    await sleep(400)
    const has = await cdp.eval(`(document.querySelector('iframe')?.getAttribute('srcdoc') || '').length > 500`)
    if (has) break
  }
  await sleep(900)
  await cdp.shot(path.join(OUT, `split-${String(n).padStart(2, '0')}.png`))
  n++

  // 开对比
  await cdp.eval(`[...document.querySelectorAll('button')].find((b) => b.textContent.includes('对比'))?.click()`)
  await sleep(1200)
  for (let i = 0; i < 8; i++) {
    await cdp.shot(path.join(OUT, `split-${String(n).padStart(2, '0')}.png`))
    n++
    await sleep(500)
  }
  console.log(`  split: ${n} 帧`)
  await closeTab(tab)
}

const SCENES = { slider: sceneSlider, selfheal: sceneSelfheal, split: sceneSplit }

async function main() {
  for (let i = 0; i < 80; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`)
      if (r.ok) break
    } catch {}
    await sleep(250)
  }
  const want = process.argv.slice(2).filter((a) => SCENES[a])
  const names = want.length ? want : Object.keys(SCENES)
  for (const name of names) {
    process.stdout.write(`截取 ${name} ...\n`)
    await SCENES[name]()
  }
}

main()
  .then(() => {
    console.log(`帧目录：${OUT}`)
    chrome.kill()
    process.exit(0)
  })
  .catch((e) => {
    console.error('截帧失败：', e.message)
    chrome.kill()
    process.exit(1)
  })