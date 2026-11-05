/**
 * 07 · 交互功能（真实浏览器）
 *
 * 覆盖两个「创新点」：
 *   「先猜后试」——挑战卡先要用户选猜测，选了才提示去验证
 *   「双沙盒同屏对比」——切到对比模式后是两个独立 iframe，可同步重置
 */
import { suite, skipped } from './lib/assert.mjs'
import { findChrome, probeServices, sleep, startGeneration, waitHydrated, withChrome } from './lib/browser.mjs'

if (!findChrome()) process.exit(skipped('未找到 Chrome/Edge（可设 CHROME_PATH）'))
const svc = await probeServices()
if (!svc.backend || !svc.frontend) {
  process.exit(skipped(`服务未就绪 backend=${svc.backend} frontend=${svc.frontend}`))
}

const t = suite('07 · 交互功能')
const CONCEPT = '演示单摆的阻尼振动：可调摆长、阻尼系数和重力加速度'

await withChrome(async ({ newPage }) => {
  const cdp = await newPage('http://localhost:3000')
  if (!t.ok('页面已水合', await waitHydrated(cdp))) return

  // 用模板概念生成，2 秒左右出结果
  await cdp.eval(`(() => {
    const ta = document.querySelector('textarea');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(ta, ${JSON.stringify(CONCEPT)});
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  })()`)

  const started = await startGeneration(cdp)
  if (!t.ok('生成已启动', started.loading || started.hasLab || started.err, JSON.stringify(started))) return

  let ready = false
  for (let i = 0; i < 40; i++) {
    await sleep(500)
    ready = await cdp.eval(`(document.querySelector('iframe')?.getAttribute('srcdoc') || '').length > 500`)
    if (ready) break
  }
  if (!t.ok('沙盒已渲染', ready)) return

  // ---- 先猜后试 ----
  const guessButtons = await cdp.eval(`(() => {
    const labels = ['会变大 ↑', '会变小 ↓', '基本不变 →'];
    return labels.filter((l) => [...document.querySelectorAll('button')].some((b) => b.textContent.trim() === l)).length;
  })()`)
  t.ok('挑战卡给出 3 个猜测选项', guessButtons === 3, String(guessButtons))

  await cdp.eval(`[...document.querySelectorAll('button')].find((b) => b.textContent.trim() === '会变大 ↑')?.click()`)
  await sleep(300)
  const locked = await cdp.eval(`document.body.innerText.includes('已锁定猜测')`)
  t.ok('选择后进入「已锁定」状态', locked)
  const stillHasButtons = await cdp.eval(
    `[...document.querySelectorAll('button')].some((b) => b.textContent.trim() === '会变小 ↓')`
  )
  t.ok('锁定后不再重复给选项', !stillHasButtons)

  // ---- 双沙盒同屏对比 ----
  const toggled = await cdp.eval(`(() => {
    const b = [...document.querySelectorAll('button')].find((x) => x.textContent.includes('对比模式'));
    if (!b) return 'no-button'; b.click(); return 'clicked';
  })()`)
  t.ok('找到并点击对比模式', toggled === 'clicked', toggled)
  await sleep(800)

  const frames = await cdp.eval(`(() => {
    const fs = [...document.querySelectorAll('iframe')];
    return { n: fs.length, withContent: fs.filter((f) => (f.getAttribute('srcdoc') || '').length > 500).length };
  })()`)
  t.ok('同屏出现两块沙盒', frames.n === 2, JSON.stringify(frames))
  t.ok('两块都装载了内容', frames.withContent === 2, JSON.stringify(frames))

  const reset = await cdp.eval(`(() => {
    const b = [...document.querySelectorAll('button')].find((x) => x.textContent.includes('同步重置'));
    if (!b) return 'no-button'; b.click(); return 'clicked';
  })()`)
  await sleep(800)
  const afterReset = await cdp.eval(`document.querySelectorAll('iframe').length`)
  t.ok('同步重置后仍是两块', reset === 'clicked' && afterReset === 2, `reset=${reset} n=${afterReset}`)

  // ---- 刷新后不丢（localStorage 恢复）----
  await cdp.send('Page.reload')
  await sleep(2500)
  const restored = await cdp.eval(`(() => {
    const src = document.querySelector('iframe')?.getAttribute('srcdoc') || '';
    return { len: src.length, banner: document.body.innerText.includes('已恢复上次实验') };
  })()`)
  t.ok('刷新后自动恢复上次实验', restored.len > 500, `${restored.len} 字符`)
  t.ok('显示「已恢复」提示', restored.banner)

  // ---- 取消生成 ----
  // 提示词必须每次唯一：否则命中缓存后 50ms 就返回，"生成中"根本抓不到
  const slowPrompt = `演示量子隧穿的概率波穿透势垒（无模板走慢路径 · 用例 ${Date.now()}）`
  await cdp.eval(`(() => {
    const ta = document.querySelector('textarea');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(ta, ${JSON.stringify(slowPrompt)});
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  })()`)

  // 刷新之后要重新等水合，否则这一下点击是空点
  await waitHydrated(cdp)
  const starting = await startGeneration(cdp, { requireLoading: true })
  if (!t.ok('慢路径生成已启动', starting.loading, JSON.stringify(starting))) return

  const cancelBtn = await cdp.eval(`(() => {
    const b = [...document.querySelectorAll('button')].find((x) => x.textContent.includes('取消生成'));
    if (!b) return 'no-button'; b.click(); return 'clicked';
  })()`)
  t.ok('生成中出现取消按钮', cancelBtn === 'clicked', cancelBtn)

  let cancelled = false
  for (let i = 0; i < 20; i++) {
    await sleep(250)
    cancelled = await cdp.eval(`document.body.innerText.includes('已取消')`)
    if (cancelled) break
  }
  t.ok('取消后给出明确提示', cancelled)
  const backToIdle = await cdp.eval(
    `[...document.querySelectorAll('button')].some((b) => b.textContent.includes('立即生成'))`
  )
  t.ok('取消后按钮恢复可用', backToIdle)

  t.ok('全程无页面异常', cdp.errors().length === 0, cdp.errors().slice(0, 1).join(' | '))
})

process.exit(t.done())