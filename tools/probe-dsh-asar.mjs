#!/usr/bin/env node
/**
 * tools/probe-dsh-asar.mjs
 *
 * 从已安装的 DeepSeek Harness 里抽取 dsh 源码，用于插件 API 探针与契约测试。
 * 只读 app.asar，不修改安装目录；产物落在 .probe/（已 gitignore）。
 *
 * 用法：
 *   node tools/probe-dsh-asar.mjs                    # 抽取 @deepseek-ai/* 与插件开发技能
 *   node tools/probe-dsh-asar.mjs --list cordis      # 只列出路径
 *   node tools/probe-dsh-asar.mjs --asar <path>      # 指定 app.asar
 */
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const DEFAULT_ASAR = path.join(
  process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'),
  'Programs',
  'DeepSeek Harness',
  'resources',
  'app.asar'
)

const args = process.argv.slice(2)
const opt = (name, fallback) => {
  const i = args.indexOf(name)
  return i >= 0 ? args[i + 1] : fallback
}
const ASAR = opt('--asar', DEFAULT_ASAR)
const LIST_ONLY = args.includes('--list')
const PATTERN = args.includes('--list') ? (args[args.indexOf('--list') + 1] || '').toLowerCase() : ''
const OUT = path.resolve('.probe', 'asar')

if (!fs.existsSync(ASAR)) {
  console.error(`未找到 app.asar：${ASAR}\n用 --asar 指定路径。`)
  process.exit(1)
}

/** asar 头部：u32@4 = pickle 总长，u32@12 = JSON 长度，JSON 从 16 开始 */
function readHeader(file) {
  const fd = fs.openSync(file, 'r')
  const head = Buffer.alloc(16)
  fs.readSync(fd, head, 0, 16, 0)
  const size = head.readUInt32LE(4)
  const jsonLen = head.readUInt32LE(12)
  const buf = Buffer.alloc(jsonLen)
  fs.readSync(fd, buf, 0, jsonLen, 16)
  fs.closeSync(fd)
  return { header: JSON.parse(buf.toString('utf8')), dataStart: 8 + size }
}

function* walk(node, prefix = '') {
  for (const [name, meta] of Object.entries(node.files || {})) {
    const p = prefix ? `${prefix}/${name}` : name
    if (meta.files) yield* walk(meta, p)
    else yield [p, meta]
  }
}

const { header, dataStart } = readHeader(ASAR)
const entries = [...walk(header)]
console.log(`asar 条目：${entries.length}，数据起点 ${dataStart}`)

if (LIST_ONLY) {
  const hits = entries.filter(([p]) => p.toLowerCase().includes(PATTERN))
  console.log(`匹配 "${PATTERN}"：${hits.length}`)
  for (const [p, m] of hits.slice(0, 100)) console.log(`  ${String(m.size).padStart(9)}  ${p}`)
  process.exit(0)
}

const WANT = [
  'dsh/node_modules/@deepseek-ai/',
  'cordis-plugin-development',
]
const KEEP = /\.(js|mjs|cjs|json|yml|yaml|md|ts|txt)$/i

const fd = fs.openSync(ASAR, 'r')
let written = 0
for (const [p, meta] of entries) {
  if (!WANT.some((w) => p.startsWith(w) || p.includes(w))) continue
  if (!KEEP.test(p) || meta.unpacked) continue
  const size = meta.size || 0
  const offset = Number(meta.offset || 0)
  const buf = Buffer.alloc(size)
  fs.readSync(fd, buf, 0, size, dataStart + offset)
  const dst = path.join(OUT, p.replace(/\//g, path.sep))
  fs.mkdirSync(path.dirname(dst), { recursive: true })
  fs.writeFileSync(dst, buf)
  written++
}
fs.closeSync(fd)

console.log(`已导出 ${written} 个文件 -> ${OUT}`)
console.log(`提示：DSH_TOOLS_PATH=${path.join(OUT, 'dsh', 'node_modules', '@deepseek-ai', 'dsh-tools', 'lib', 'index.js')}`)