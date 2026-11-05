#!/usr/bin/env node
/**
 * tools/capture-frames.mjs
 *
 * 用真实 Chrome 截取实验室画面，产出 README 需要的素材帧：
 *   assets/_frames/<lab>-<n>.png
 *
 * 只依赖 CDP（Node 内置 WebSocket），不需要 puppeteer。
 * 帧序列用于后续 tools/build-assets.py 合成 GIF。
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

const PORT = 9411
const ROOT = path.resolve('.')
const OUT = path.join(ROOT, 'assets', '_frames')
const W = Number(process.env.FRAME_W || 1280)
const H = Number(process.env.FRAME_H || 800)
const FRAMES_PER_LAB = Number(process.env.FRAMES_PER_LAB || 5)
const GAP_MS = Number(process.env.FRAME_GAP_MS || 260)

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const LABS = [
  ['lorenz', 'B-模板化生成/out/lorenz.html'],
  ['wave', 'B-模板化生成/out/wave.html'],
  ['efield', 'B-模板化生成/out/efield.html'],
  ['orbit', 'B-模板化生成/out/orbit.html'],
  ['projectile', 'B-模板化生成/out/projectile.html'],
  ['doppler', 'A-自由生成/gallery/labs/doppler-agentic.html'],
]

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
  send(method, params = {}, timeout = 30000) {
    const id = ++this.seq
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id)
          reject(new Error('CDP 超时 ' + method))
        }
      }, timeout)
    })
  }
  async eval(expression) {
    const r = await this.send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 200))
    return r.result?.value
  }
}

fs.rmSync(OUT, { recursive: true, force: true })
fs.mkdirSync(OUT, { recursive: true })

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'sc-frames-'))
const chrome = spawn(
  CHROME,
  [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-gpu',
    '--hide-scrollbars',
    `--window-size=${W},${H}`,
    'about:blank',
  ],
  { stdio: 'ignore' }
)

async function main() {
  for (let i = 0; i < 80; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`)
      if (r.ok) break
    } catch {}
    await sleep(250)
  }

  for (const [name, rel] of LABS) {
    const file = path.join(ROOT, rel)
    if (!fs.existsSync(file)) {
      console.warn(`跳过（缺文件）：${rel}`)
      continue
    }
    const tab = await (
      await fetch(`http://127.0.0.1:${PORT}/json/new?${encodeURIComponent(pathToFileURL(file).href)}`, {
        method: 'PUT',
      })
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

    // 等画布出现并有内容
    for (let i = 0; i < 40; i++) {
      await sleep(200)
      const ready = await cdp.eval(
        `document.readyState === 'complete' && !!document.querySelector('canvas')`
      )
      if (ready) break
    }
    await sleep(900)

    for (let n = 0; n < FRAMES_PER_LAB; n++) {
      const shot = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false })
      fs.writeFileSync(path.join(OUT, `${name}-${n}.png`), Buffer.from(shot.data, 'base64'))
      await sleep(GAP_MS)
    }
    console.log(`截取 ${name} × ${FRAMES_PER_LAB}`)
    ws.close()
    await fetch(`http://127.0.0.1:${PORT}/json/close/${tab.id}`)
  }
}

main()
  .then(() => {
    console.log(`帧目录：${OUT}`)
    chrome.kill()
    process.exit(0)
  })
  .catch((e) => {
    console.error('截图失败：', e.message)
    chrome.kill()
    process.exit(1)
  })