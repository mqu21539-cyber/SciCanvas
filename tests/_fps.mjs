/** 临时：测某个实验室页面的渲染帧率。 */
import { findChrome, sleep, withChrome } from './lib/browser.mjs'

const file = process.argv[2] || 'D:/SciCanvas/B-模板化生成/out/lorenz.html'
const seconds = Number(process.argv[3] || 2)

if (!findChrome()) {
  console.log('无浏览器')
  process.exit(2)
}

await withChrome(async ({ newPage }) => {
  const cdp = await newPage('file:///' + file)
  await sleep(2500)
  const fps = await cdp.eval(`new Promise((res) => {
    let n = 0; const t0 = performance.now();
    function tick(){
      n++;
      if (performance.now() - t0 < ${seconds * 1000}) requestAnimationFrame(tick);
      else res(+(n / ((performance.now() - t0) / 1000)).toFixed(1));
    }
    requestAnimationFrame(tick);
  })`)
  const heap = await cdp.eval('performance.memory ? Math.round(performance.memory.usedJSHeapSize/1048576) : -1')
  console.log(`${file.split('/').pop()}  FPS=${fps}  heap=${heap}MB`)
})