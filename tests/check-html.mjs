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
      const sliders = document.querySelectorAll('input[type=range]').length;
      // 全息底座用四层 SVG，旧模板用 canvas：两种都要能验，否则新模板会"假通过"
      const c = document.querySelector('canvas');
      let painted = 0, sampled = 0;
      if (c) {
        const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
        for (let i = 3; i < d.length; i += 4 * 997) { sampled++; if (d[i] > 0) painted++; }
      }
      const layers = ['l0','l1','l2','l3'].map(id => {
        const el = document.getElementById(id);
        return el ? el.childElementCount : -1;
      });
      return { canvas: !!c, painted, sampled, sliders, layers };
    })()`)
    const name = file.split(/[\\/]/).pop()
    const svgNodes = (info.layers || []).reduce((a, b) => a + Math.max(0, b), 0)
    t.ok(`${name}: 无异常`, cdp.errors().length === 0, cdp.errors().slice(0, 1).join(' | '))
    t.ok(
      `${name}: 画布已绘制`,
      (info.painted || 0) > 0 || svgNodes >= 3,
      info.layers && svgNodes >= 3 ? `SVG 层节点 ${JSON.stringify(info.layers)}` : `${info.painted}/${info.sampled} 像素`
    )
    t.ok(`${name}: 滑块`, (info.sliders || 0) >= 2, String(info.sliders))
  }
})
process.exit(t.done())