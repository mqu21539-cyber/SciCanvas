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
      // 遥测指标不能出现 NaN/undefined。踩过一次：数字滚动在 dt 赋值之前跑，
      // 首帧拿到 undefined，四个指标全变 NaN，而当时的测试一条都没抓到。
      const metrics = [...document.querySelectorAll('.metric .v')].map(e => e.textContent.trim());
      const badMetrics = metrics.filter(x => /NaN|undefined|null/i.test(x));
      const numericMetrics = metrics.filter(x => /[0-9]/.test(x)).length;
      // 每根滑块都必须能被真正点到。踩过一次：胶囊少了 position:relative，
      // 透明 range 相对整页定位，最后一根盖住全页，其它三根永远拖不动。
      const caps = [...document.querySelectorAll('.cap')].map(cap => {
        const inp = cap.querySelector('input[type=range]');
        const b = cap.getBoundingClientRect();
        const hit = document.elementFromPoint(b.left + b.width / 2, b.top + b.height - 6);
        return {
          k: inp ? inp.dataset.k : null,
          hitK: hit && hit.dataset ? hit.dataset.k : null,
        };
      });
      const deadSliders = caps.filter(c => c.k && c.hitK !== c.k);
      // 声明了画布抓握的实验：拖一下 SVG 实体层，必须真的有参数变化。
      // 只检查 class 没用——曾经 bindDrag 注册失败，class 在、拖不动。
      let dragged = null;
      const stage = document.getElementById('stage');
      const l1 = document.getElementById('l1');
      if (stage && l1 && stage.classList.contains('grabbable') && window.HOLO) {
        try {
          const keys = Object.keys(HOLO.params());
          const before = HOLO.params();
          const r = l1.getBoundingClientRect();
          const mk = (t, y, btn) => new PointerEvent(t, {
            bubbles: true, cancelable: true, pointerId: 11, buttons: btn,
            clientX: r.left + r.width / 2, clientY: y,
          });
          l1.dispatchEvent(mk('pointerdown', r.top + r.height * 0.9, 1));
          l1.dispatchEvent(mk('pointermove', r.top + r.height * 0.1, 1));
          l1.dispatchEvent(mk('pointerup', r.top + r.height * 0.1, 0));
          const after = HOLO.params();
          dragged = keys.some((k) => before[k] !== after[k]);
        } catch (e) {
          dragged = 'ERR: ' + (e && e.message);
        }
      }
      return { canvas: !!c, painted, sampled, sliders, layers, metrics, badMetrics, numericMetrics, caps, deadSliders, dragged };
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
    t.ok(
      `${name}: 遥测指标无 NaN`,
      (info.badMetrics || []).length === 0,
      info.badMetrics && info.badMetrics.length
        ? `异常值 ${JSON.stringify(info.badMetrics)} · 全部 ${JSON.stringify(info.metrics)}`
        : `全部 ${JSON.stringify(info.metrics)}`
    )
    t.ok(
      `${name}: 至少一个指标是数字`,
      (info.numericMetrics || 0) > 0,
      `${info.numericMetrics}/${(info.metrics || []).length}`
    )
    if ((info.caps || []).length) {
      t.ok(
        `${name}: 每根滑块都能点到`,
        (info.deadSliders || []).length === 0,
        info.deadSliders && info.deadSliders.length
          ? `点不到 ${JSON.stringify(info.deadSliders)}`
          : `${info.caps.map((c) => c.k).join(' / ')}`
      )
    }
    if (info.dragged !== null) {
      t.ok(`${name}: 画布内可拖动改参数`, info.dragged === true, String(info.dragged))
    }
  }
})
process.exit(t.done())