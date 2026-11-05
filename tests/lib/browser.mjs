/**
 * Chrome + CDP 的最小组件（不依赖 puppeteer）。
 * 找不到 Chrome 时返回 null，调用方据此 SKIP。
 */
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const CANDIDATES = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].filter(Boolean)

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

export function findChrome() {
  for (const p of CANDIDATES) {
    try {
      if (fs.existsSync(p)) return p
    } catch {}
  }
  return null
}

class CDP {
  constructor(ws) {
    this.ws = ws
    this.seq = 0
    this.pending = new Map()
    this.events = []
    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data)
      if (msg.id && this.pending.has(msg.id)) {
        const p = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        if (msg.error) p.reject(new Error(JSON.stringify(msg.error)))
        else p.resolve(msg.result)
      } else if (msg.method) {
        this.events.push(msg)
      }
    })
  }

  send(method, params = {}, timeoutMs = 30000) {
    const id = ++this.seq
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id)
          reject(new Error(`CDP 超时: ${method}`))
        }
      }, timeoutMs)
    })
  }

  async eval(expression) {
    const r = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
      userGesture: true,
    })
    if (r.exceptionDetails) {
      throw new Error(`页面执行异常: ${JSON.stringify(r.exceptionDetails).slice(0, 240)}`)
    }
    return r.result?.value
  }

  /** 页面级错误（未捕获异常 + console.error），忽略 favicon 噪音 */
  errors() {
    return this.events
      .filter(
        (e) =>
          e.method === 'Runtime.exceptionThrown' ||
          (e.method === 'Log.entryAdded' && e.params.entry.level === 'error')
      )
      .map((e) =>
        e.method === 'Runtime.exceptionThrown'
          ? e.params.exceptionDetails?.exception?.description || e.params.exceptionDetails?.text
          : `${e.params.entry.text} @ ${e.params.entry.url || '?'}`
      )
      .filter((t) => !/favicon/i.test(String(t)))
  }
}

/**
 * 启动一个 headless Chrome，交给回调使用后自动关闭。
 * @param {(api: {newPage: (url: string) => Promise<CDP>}) => Promise<void>} fn
 */
export async function withChrome(fn, { port = 9333, width = 1440, height = 1000 } = {}) {
  const bin = findChrome()
  if (!bin) throw new Error('未找到 Chrome/Edge')

  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scicanvas-chrome-'))
  const chrome = spawn(
    bin,
    [
      '--headless=new',
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${userDataDir}`,
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-gpu',
      `--window-size=${width},${height}`,
      'about:blank',
    ],
    { stdio: 'ignore' }
  )

  const base = `http://127.0.0.1:${port}`
  for (let i = 0; i < 80; i++) {
    try {
      const r = await fetch(`${base}/json/version`)
      if (r.ok) break
    } catch {}
    await sleep(250)
  }

  const newPage = async (url) => {
    const tab = await (
      await fetch(`${base}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' })
    ).json()
    const ws = new WebSocket(tab.webSocketDebuggerUrl)
    await new Promise((r) => ws.addEventListener('open', r, { once: true }))
    const cdp = new CDP(ws)
    await cdp.send('Page.enable')
    await cdp.send('Runtime.enable')
    await cdp.send('Log.enable')
    return cdp
  }

  try {
    await fn({ newPage, bin })
  } finally {
    try {
      chrome.kill()
    } catch {}
  }
}

/** 服务可用性探测 */
export async function probeServices() {
  const out = {}
  for (const [key, url] of [
    ['backend', 'http://127.0.0.1:8000/api/health'],
    ['frontend', 'http://localhost:3000'],
  ]) {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(3000) })
      out[key] = r.ok
    } catch {
      out[key] = false
    }
  }
  return out
}

/**
 * 等 React 水合完成。
 * dev 模式首次访问要现场编译，DOM 先到、事件监听后到，此时点击是空点。
 * 受控 textarea 上会有 React 挂的 _valueTracker，可作为水合完成的信号。
 */
export async function waitHydrated(cdp, timeoutMs = 25000) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    const ready = await cdp.eval(
      `!!(document.querySelector('textarea') && document.querySelector('textarea')._valueTracker)`
    )
    if (ready) return true
    await sleep(250)
  }
  return false
}

/**
 * 点击「立即生成」，并确认这一下真的生效了。
 * 判据：按钮进入取消态 / 出现沙盒 / 出现错误横幅——三者任一即算启动。
 * 都不满足就再点一次（最多 attempts 次），避免把水合慢当成产品 bug。
 */
export async function startGeneration(cdp, { attempts = 6, gapMs = 1200, requireLoading = false } = {}) {
  let last = { loading: false, hasLab: false, err: false }
  for (let i = 0; i < attempts; i++) {
    await cdp.eval(
      `[...document.querySelectorAll('button')].find((b) => b.textContent.includes('立即生成'))?.click()`
    )
    await sleep(gapMs)
    last = await cdp.eval(`(() => ({
      loading: [...document.querySelectorAll('button')].some((b) => /取消/.test(b.textContent)),
      hasLab: (document.querySelector('iframe')?.getAttribute('srcdoc') || '').length > 500,
      err: document.body.innerText.includes('生成失败'),
    }))()`)
    // requireLoading：页面上原本就有沙盒时，"出现了沙盒"不能当作启动成功的证据
    if (last.loading || (!requireLoading && (last.hasLab || last.err))) return last
  }
  return last
}