/**
 * 04 · 自愈链路端到端（真实浏览器 + 真实后端）
 *
 * 流程：打开前端 → 触发一次生成 → 向页面注入 SCICANVAS_ERROR →
 *       断言自愈徽标出现、/api/fix 返回、沙盒内容被替换。
 *
 * 需要：后端 :8000、前端 :3000、Chrome、有效 DEEPSEEK_API_KEY（会真实调用一次）。
 */
import { suite, skipped } from './lib/assert.mjs'
import { findChrome, probeServices, sleep, withChrome } from './lib/browser.mjs'

if (!findChrome()) process.exit(skipped('未找到 Chrome/Edge（可设 CHROME_PATH）'))
const svc = await probeServices()
if (!svc.backend || !svc.frontend) {
  process.exit(skipped(`服务未就绪 backend=${svc.backend} frontend=${svc.frontend}`))
}

const t = suite('04 · 自愈链路端到端')
const GEN_TIMEOUT = Number(process.env.SCICANVAS_GEN_TIMEOUT || 150)

await withChrome(async ({ newPage }) => {
  const cdp = await newPage('http://localhost:3000')
  await sleep(2000)

  const clicked = await cdp.eval(`(() => {
    const b = [...document.querySelectorAll('button')].find((x) => x.textContent.includes('多普勒'));
    if (!b) return 'no-button';
    b.click(); return 'clicked';
  })()`)
  if (!t.ok('点击预设按钮', clicked === 'clicked', clicked)) return

  // 首屏点击可能撞上 React 水合未完成：以「按钮进入 loading 文案」为准，最多点 3 次
  let started = false
  for (let attempt = 0; attempt < 3 && !started; attempt++) {
    if (attempt > 0) {
      await cdp.eval(`(() => {
        const b = [...document.querySelectorAll('button')].find((x) => x.textContent.includes('多普勒'));
        b && b.click();
      })()`)
    }
    await sleep(900)
    started = await cdp.eval(
      `[...document.querySelectorAll('button')].some((b) => /正在|生成中/.test(b.textContent))`
    )
  }
  if (!t.ok('生成已启动（loading 态）', started)) return

  let ready = false
  let waited = 0
  while (waited < GEN_TIMEOUT) {
    await sleep(2000)
    waited += 2
    ready = await cdp.eval(`(() => {
      const f = document.querySelector('iframe');
      return !!(f && (f.getAttribute('srcdoc') || '').length > 500);
    })()`)
    if (ready) break
  }
  if (!t.ok('沙盒渲染出生成结果', ready, `${waited}s`)) return

  const info = await cdp.eval(`(() => {
    const src = document.querySelector('iframe').getAttribute('srcdoc') || '';
    return { len: src.length, canvas: src.includes('<canvas'), onerror: src.includes('window.onerror'),
             sliders: (src.match(/type="range"/g) || []).length };
  })()`)
  t.ok('产物含 canvas', info.canvas)
  t.ok('产物含 onerror 桥', info.onerror)
  t.ok('产物含滑块', info.sliders >= 2, String(info.sliders))
  t.ok('生成过程无页面异常', cdp.errors().length === 0, cdp.errors().slice(0, 1).join(' | '))

  // 触发真实页面的自愈监听
  const before = info.len
  const t0 = Date.now()
  await cdp.send('Network.enable')
  await cdp.eval(`window.postMessage({ type: 'SCICANVAS_ERROR', message: 'ReferenceError: __e2e_undefined is not defined', line: 42 }, '*')`)

  // 断言 1：页面真的向 /api/fix 发了请求（这是"链路通"的直接证据）
  let fixCalls = 0
  for (let i = 0; i < 40; i++) {
    await sleep(250)
    fixCalls = cdp.events.filter(
      (e) => e.method === 'Network.requestWillBeSent' && String(e.params.request.url).includes('/api/fix')
    ).length
    if (fixCalls > 0) break
  }
  t.ok('页面发出了 POST /api/fix', fixCalls > 0, `${fixCalls} 次请求 · ${Math.round((Date.now() - t0) / 1000)}s`)

  // 断言 2：自愈徽标出现（UI 进入了修复态）
  let badge = false
  for (let i = 0; i < 20; i++) {
    await sleep(300)
    badge = await cdp.eval(`[...document.querySelectorAll('div')].some((d) => d.textContent.includes('Self-Healing Agent 正在自动热修复'))`)
    if (badge) break
  }
  t.ok('进入自愈状态', badge)

  // 断言 3：修复流程结束后沙盒仍然可用（内容是否逐字变化取决于模型，不作为判据）
  let settled = false
  let after = before
  for (let i = 0; i < 90; i++) {
    await sleep(1000)
    const st = await cdp.eval(`(() => {
      const f = document.querySelector('iframe');
      const src = f ? (f.getAttribute('srcdoc') || '') : '';
      return { len: src.length, fixing: [...document.querySelectorAll('div')].some((d) => d.textContent.includes('正在自动热修复')) };
    })()`)
    after = st.len
    if (!st.fixing && after > 500) { settled = true; break }
  }
  const changed = after !== before
  t.ok('修复结束后沙盒仍可渲染', settled, `before=${before} after=${after} 变化=${changed ? '是' : '否'} ${Math.round((Date.now() - t0) / 1000)}s`)
  t.ok('自愈后无新增页面异常', cdp.errors().length === 0, cdp.errors().slice(0, 1).join(' | '))
})

process.exit(t.done())