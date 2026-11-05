/**
 * 测试结果记录：统一 PASS / FAIL / SKIP 与退出码。
 * 退出码：0 全过（可含 SKIP）、1 有失败、2 全部跳过。
 */
export function suite(title) {
  const rows = []
  let pass = 0
  let fail = 0
  let skip = 0

  console.log(`\n${title}`)
  console.log('─'.repeat(Math.min(title.length + 4, 60)))

  return {
    ok(label, cond, extra = '') {
      if (cond) {
        pass++
        console.log(`  PASS  ${label}${extra ? `  [${extra}]` : ''}`)
      } else {
        fail++
        console.log(`  FAIL  ${label}${extra ? `  [${extra}]` : ''}`)
      }
      rows.push({ label, status: cond ? 'pass' : 'fail', extra })
      return Boolean(cond)
    },
    skip(label, reason) {
      skip++
      console.log(`  SKIP  ${label}  [${reason}]`)
      rows.push({ label, status: 'skip', extra: reason })
    },
    get pass() { return pass },
    get fail() { return fail },
    get skip() { return skip },
    done() {
      console.log(`\n  小计：通过 ${pass} / 失败 ${fail} / 跳过 ${skip}`)
      if (fail > 0) return 1
      if (pass === 0) return 2
      return 0
    },
  }
}

/** 跳过整组并返回退出码 2 */
export function skipped(reason) {
  console.log(`  SKIP  整组跳过  [${reason}]`)
  return 2
}