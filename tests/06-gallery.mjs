/**
 * 06 · 展厅清单一致性
 *
 * 插件会把新实验自动登记进 manifest.json，所以这里守住两件事：
 *   1) 每一条登记的文件都真实存在（防止插件写坏路径留下死链）
 *   2) 字段齐全（id/title/category/file），id 不重复
 */
import fs from 'node:fs'
import path from 'node:path'
import { suite } from './lib/assert.mjs'
import { ROOT } from './lib/dsh-tools.mjs'

const GALLERY = path.join(ROOT, 'gallery')
const MANIFEST = path.join(GALLERY, 'manifest.json')

const t = suite('06 · 展厅清单一致性')

if (!fs.existsSync(MANIFEST)) {
  t.ok('manifest.json 存在', false, MANIFEST)
  process.exit(t.done())
}

let entries
try {
  entries = JSON.parse(fs.readFileSync(MANIFEST, 'utf-8'))
} catch (e) {
  t.ok('manifest.json 可解析', false, e.message.slice(0, 60))
  process.exit(t.done())
}

t.ok('manifest 可解析且是数组', Array.isArray(entries), `${entries.length} 条`)
t.ok('至少 4 个实验', entries.length >= 4, String(entries.length))

const missing = []
const badFields = []
for (const e of entries) {
  for (const key of ['id', 'title', 'category', 'file']) {
    if (!e || !e[key]) badFields.push(`${e?.id || '?'} 缺 ${key}`)
  }
  if (e?.file) {
    const abs = path.resolve(GALLERY, e.file)
    if (!fs.existsSync(abs)) missing.push(`${e.id} -> ${e.file}`)
  }
}
t.ok('每条都有必填字段', badFields.length === 0, badFields.slice(0, 2).join('; '))
t.ok('登记的文件都真实存在', missing.length === 0, missing.slice(0, 3).join('; '))

const ids = entries.map((e) => e.id)
t.ok('id 不重复', new Set(ids).size === ids.length, ids.join(','))

// 页面内联的降级清单（file:// 打开时用那份）必须是 manifest 的子集：
// 插件随时会新增实验，不强制同步；但反向过期（指向已删除的实验）必须拦住。
const indexHtml = fs.readFileSync(path.join(GALLERY, 'index.html'), 'utf-8')
const fallbackIds = [...indexHtml.matchAll(/id:\s*"([a-z0-9-_]+)"/g)].map((m) => m[1])
const stale = fallbackIds.filter((id) => !ids.includes(id))
t.ok('页面降级清单无过期条目', stale.length === 0, stale.join(', '))

const manifestOnly = ids.filter((id) => !fallbackIds.includes(id))
if (manifestOnly.length) {
  console.log(`  提示  仅 manifest 有（file:// 打开看不到）：${manifestOnly.join(', ')}`)
}

process.exit(t.done())