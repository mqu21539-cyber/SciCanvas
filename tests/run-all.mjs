#!/usr/bin/env node
/**
 * 一键回归：node tests/run-all.mjs [--fast] [--only 03] [--list]
 *
 * 每个测试自己判断前置条件，不满足就 SKIP（退出码 2），不会误报失败。
 * 退出码：0 全过、1 有失败、2 全部跳过。
 */
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { findChrome, probeServices } from './lib/browser.mjs'

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'))
const ROOT = path.resolve(HERE, '..')
const args = process.argv.slice(2)
const FAST = args.includes('--fast')
const ONLY = args.includes('--only') ? args[args.indexOf('--only') + 1] : null

const PY_CANDIDATES = [
  process.env.SCICANVAS_PYTHON,
  path.join(ROOT, 'A-自由生成', 'backend', '.venv', 'Scripts', 'python.exe'),
  path.join(ROOT, 'A-自由生成', 'backend', '.venv', 'bin', 'python'),
  'python',
]
const PY = PY_CANDIDATES.find((p) => p === 'python' || (p && fs.existsSync(p))) || 'python'

const TESTS = [
  {
    id: '00',
    name: '后端冒烟（路由/校验/桩流水线）',
    cmd: PY,
    argv: ['smoke_test.py'],
    cwd: path.join(ROOT, 'A-自由生成', 'backend'),
    slow: false,
  },
  { id: '01', name: '插件契约（dsh defineTool）', cmd: 'node', file: '01-plugin-contract.mjs', slow: false },
  { id: '02', name: '混合路由（真实 API）', cmd: PY, file: '02-routing.py', slow: true },
  { id: '03', name: '模板渲染 + 浏览器验证', cmd: 'node', file: '03-templates.mjs', slow: true },
  { id: '04', name: '自愈链路端到端', cmd: 'node', file: '04-selfheal.mjs', slow: true, needsServices: true },
  { id: '05', name: '前端路由徽标', cmd: 'node', file: '05-ui-route.mjs', slow: true, needsServices: true },
  { id: '06', name: '展厅清单一致性', cmd: 'node', file: '06-gallery.mjs', slow: false },
  { id: '07', name: '交互功能（猜卡 / 双沙盒）', cmd: 'node', file: '07-ui-features.mjs', slow: true, needsServices: true },
  { id: '08', name: 'arXiv 摘要直读', cmd: PY, file: '08-arxiv.py', slow: true, needsServices: true },
]

if (args.includes('--list')) {
  for (const t of TESTS) console.log(`${t.id}  ${t.name}${t.slow ? '  (slow)' : ''}`)
  process.exit(0)
}

const selected = TESTS.filter((t) => (!ONLY || t.id === ONLY) && (!FAST || !t.slow))
if (!selected.length) {
  console.error('没有匹配的测试')
  process.exit(1)
}

// ---- 环境概览 ----
const chrome = findChrome()
const svc = await probeServices()
const dshTools = fs.existsSync(path.join(ROOT, '.probe', 'probe', 'node_modules', '@deepseek-ai', 'dsh-tools'))
const venvOk = fs.existsSync(path.join(ROOT, 'A-自由生成', 'backend', '.venv'))

console.log('\nSciCanvas 回归测试')
console.log('='.repeat(56))
console.log(`  仓库      ${ROOT}`)
console.log(`  Python    ${PY}${venvOk ? '' : '  (未找到 backend/.venv)'}`)
console.log(`  Chrome    ${chrome || '未找到（浏览器类测试会 SKIP）'}`)
console.log(`  dsh-tools ${dshTools ? '已抽取' : '未抽取（插件契约测试会 SKIP）'}`)
console.log(`  后端      ${svc.backend ? 'UP' : 'DOWN'}   前端 ${svc.frontend ? 'UP' : 'DOWN'}`)
console.log(`  用例      ${selected.map((t) => t.id).join(', ')}${FAST ? '  (--fast)' : ''}`)
console.log('='.repeat(56))

// ---- 逐个跑 ----
const results = []
for (const t of selected) {
  const started = Date.now()
  const isNode = t.cmd === 'node'
  const argv = isNode ? [path.join(HERE, t.file)] : t.argv || [path.join(HERE, t.file)]
  const res = spawnSync(isNode ? process.execPath : t.cmd, argv, {
    cwd: t.cwd || HERE,
    stdio: 'inherit',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  })
  const code = res.status === null ? 1 : res.status
  results.push({ id: t.id, name: t.name, code, ms: Date.now() - started })
}

// ---- 汇总 ----
const label = (c) => (c === 0 ? 'PASS' : c === 2 ? 'SKIP' : 'FAIL')
console.log('\n' + '='.repeat(56))
console.log('  汇总')
console.log('-'.repeat(56))
for (const r of results) {
  console.log(`  ${label(r.code).padEnd(5)} ${r.id}  ${r.name}  (${(r.ms / 1000).toFixed(1)}s)`)
}
const failed = results.filter((r) => r.code === 1)
const passed = results.filter((r) => r.code === 0)
const skippedTests = results.filter((r) => r.code === 2)
console.log('-'.repeat(56))
console.log(`  通过 ${passed.length} / 失败 ${failed.length} / 跳过 ${skippedTests.length}`)
console.log('='.repeat(56) + '\n')

process.exit(failed.length ? 1 : passed.length ? 0 : 2)