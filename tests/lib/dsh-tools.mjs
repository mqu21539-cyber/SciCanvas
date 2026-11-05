/**
 * 定位并加载 dsh 自己的 @deepseek-ai/dsh-tools。
 *
 * 三种来源，按优先级：
 *   1. 裸标识符（在 dsh profile 目录里跑时可直接解析）
 *   2. 环境变量 DSH_TOOLS_PATH（指向 .../dsh-tools/lib/index.js）
 *   3. 仓库内本地探针 .probe/...（由 tools/probe-dsh-asar 抽出）
 */
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'))
export const ROOT = path.resolve(HERE, '..', '..')

export async function loadDshTools() {
  try {
    return { mod: await import('@deepseek-ai/dsh-tools'), from: 'bare specifier' }
  } catch {}

  const candidates = [
    process.env.DSH_TOOLS_PATH,
    path.join(ROOT, '.probe', 'probe', 'node_modules', '@deepseek-ai', 'dsh-tools', 'lib', 'index.js'),
    path.join(ROOT, '.probe', 'asar', 'dsh', 'node_modules', '@deepseek-ai', 'dsh-tools', 'lib', 'index.js'),
  ].filter(Boolean)

  for (const file of candidates) {
    if (fs.existsSync(file)) {
      return { mod: await import(pathToFileURL(file).href), from: file }
    }
  }
  return null
}