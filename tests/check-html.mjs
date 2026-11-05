/**
 * 临时：验证插件产出的实验室在真实浏览器里能跑（无异常 + 画布有像素）。
 */
import { pathToFileURL } from 'node:url'
import { suite, skipped } from './lib/assert.mjs'
import { findChrome, sleep, withChrome } from './lib/browser.mjs'

const FILES = process.argv.slice(2)
if (!FILES.length) {
  console.log('用法: node check-labs.mjs <file.html> [...]')
  process.exit(2)
}
if (!findChrome()) process.exit(skipped('未找到 Chrome'))

const t = suite('临时 · 指定实验室浏览器验证')
await withChrome(async ({ newPage }) => {
  for (const file of FILES) {
    const cdp = await newPage(pathToFileURL(file).href)
    let ready = false
    for (let i = 0; i < 25; i++) {
      await sleep(200)
      ready = await cdp.eval(`document.readyState === 'complete' && !!document.querySelector('canvas')`)
      if (ready) break
    }
    await sleep(700)
    const info = await cdp.eval(`(() => {
      const c = document.querySelector('canvas');
      if (!c) return { canvas: false };
      let painted = 0, sampled = 0;
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      for (let i = 3; i < d.length; i += 4 * 997) { sampled++; if (d[i] > 0) painted++; }
      return { canvas: true, painted, sampled, sliders: document.querySelectorAll('input[type=range]').length };
    })()`)
    const name = file.split(/[\\/]/).pop()
    t.ok(`${name}: 无异常`, cdp.errors().length === 0, cdp.errors().slice(0, 1).join(' | '))
    t.ok(`${name}: 画布已绘制`, (info.painted || 0) > 0, `${info.painted}/${info.sampled}`)
    t.ok(`${name}: 滑块`, (info.sliders || 0) >= 2, String(info.sliders))
  }
})
process.exit(t.done())