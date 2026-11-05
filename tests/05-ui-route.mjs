/**
 * 05 · 前端路由徽标（真实 UI）
 *
 * 输入一个模板能覆盖的概念（单摆），断言：
 *   顶部徽标显示「模板 · oscillator」且 10 秒内出结果、沙盒已渲染。
 */
import { suite, skipped } from './lib/assert.mjs'
import { findChrome, probeServices, sleep, startGeneration, waitHydrated, withChrome } from './lib/browser.mjs'

if (!findChrome()) process.exit(skipped('未找到 Chrome/Edge（可设 CHROME_PATH）'))
const svc = await probeServices()
if (!svc.backend || !svc.frontend) {
  process.exit(skipped(`服务未就绪 backend=${svc.backend} frontend=${svc.frontend}`))
}

const t = suite('05 · 前路由徽标')
const CONCEPT = '演示单摆的阻尼振动：可调摆长、阻尼系数和重力加速度，观察振幅如何衰减'

await withChrome(async ({ newPage }) => {
  const cdp = await newPage('http://localhost:3000')
  if (!t.ok('页面已水合', await waitHydrated(cdp))) return

  // React 受控 textarea 必须走原生 setter + input 事件
  const typed = await cdp.eval(`(() => {
    const ta = document.querySelector('textarea');
    if (!ta) return 'no-textarea';
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(ta, ${JSON.stringify(CONCEPT)});
    ta.dispatchEvent(new Event('input', { bubbles: true }));
    return ta.value.slice(0, 10);
  })()`)
  if (!t.ok('填入自定义概念', typed !== 'no-textarea', String(typed))) return

  const started = await startGeneration(cdp)
  if (!t.ok('生成已启动', started.loading || started.hasLab || started.err, JSON.stringify(started))) return

  const t0 = Date.now()
  let badge = ''
  for (let i = 0; i < 40; i++) {
    await sleep(500)
    badge = await cdp.eval(`(() => {
      const s = [...document.querySelectorAll('span')].map((x) => x.textContent)
        .find((x) => x && (x.startsWith('模板 ·') || x.startsWith('双 Agent ·')));
      return s || '';
    })()`)
    if (badge) break
  }
  const secs = (Date.now() - t0) / 1000

  t.ok('出现引擎徽标', Boolean(badge), badge)
  t.ok('走模板快路径', badge.startsWith('模板 ·'), badge)
  t.ok('10 秒内返回', secs < 10, `${secs.toFixed(1)}s`)

  const state = await cdp.eval(`(() => {
    const src = document.querySelector('iframe')?.getAttribute('srcdoc') || '';
    return { len: src.length, canvas: src.includes('<canvas>') || src.includes('<canvas ') };
  })()`)
  t.ok('沙盒已渲染', state.len > 500 && state.canvas, JSON.stringify(state))
})

process.exit(t.done())