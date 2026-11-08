# 全息 2.5D 底座：模板作者手册

`holo_shell.py` 把「四层 Z 轴拆解、双通道示波器、子弹时间、四套滤镜、平行残影、
靶向锁定、自动运镜」这些交互一次性写好。**模板只需要写两个函数**，剩下的都白送。

## 最小可运行模板

```python
import holo_shell

META = {
    "name": "mylab",
    "title": "我的实验",
    "category": "学科 / 分支",
    "formula": "y = a·x + b",
    "controls": [
        {"id": "a", "label": "斜率", "unit": "", "min": 0.1, "max": 5, "step": 0.1, "default": 1},
    ],
    "metrics": [{"id": "y", "label": "当前 y"}],
    "challenge": "斜率翻倍，交点会怎么移动？",
}

_JS = r"""
(function(){
  var P = HOLO.P;                 // 参数（由 controls 自动生成滑块）
  var S = { x: 0 };

  window.reset = function(){      // 参数变化 / 重置时调用
    S.x = 0;
    HOLO.L0('<line x1="0" y1="200" x2="700" y2="200" stroke="#38bdf8"/>');
  };

  window.frame = function(dt, t){ // 每帧调用；dt 已乘过时间膨胀系数
    S.x += dt * 30;
    HOLO.L1('<circle cx="' + S.x + '" cy="200" r="10" fill="url(#sphere-cyan)"/>');
    HOLO.L2(''); HOLO.L3('');
    HOLO.telemetry(S.x / 700);    // 推到示波器（0~1）
    HOLO.metric('y', (P.a * S.x).toFixed(1));
  };
})();
"""

def build(params, copy):
    controls = [dict(c, default=params.get(c["id"], c["default"])) for c in META["controls"]]
    return holo_shell.render(
        {
            "title": copy["title"],
            "subtitle": copy["subtitle"],
            "formula": copy["formula"],
            "controls": controls,
            "metrics": META["metrics"],
        },
        _JS,
    )
```

## 四层各画什么

| 层 | 放什么 | 建议 |
| :--- | :--- | :--- |
| `L0` | 坐标轴、网格、刻度、静态轨道 | 变化少，写一次就行（相同内容自动跳过重绘） |
| `L1` | 实验主体：球、滑块、粒子、杆 | 用 `url(#sphere-cyan)` / `url(#sphere-amber)` / `url(#block-3d)` 得到拟物光影 |
| `L2` | 力矢量、速度箭头、运动尾迹 | 箭头用 `marker-end="url(#ar-cyan)"`，发光挂 `filter="url(#neon-glow)"` |
| `L3` | 实时读数面板、靶向准星 | 用 `<g transform="translate(...)">` 当固定面板 |

## 能用的 API

| 调用 | 作用 |
| :--- | :--- |
| `HOLO.P` / `HOLO.p(key)` | 当前参数 |
| `HOLO.L0..L3(html)` | 往对应层写 SVG 片段（内容没变会自动跳过） |
| `HOLO.telemetry(a, b)` | 推两个 0~1 值到双通道示波器（只传一个就是单通道） |
| `HOLO.metric(id, text)` | 更新右侧指标卡 |
| `HOLO.iso(x, y, z)` | 等距投影，要做伪 3D 时用 |
| `HOLO.highlight()` | 当前被悬停锁定的参数名（用来画准星） |
| `HOLO.ghostActive()` | 残影是否已锁定 |

## 宿主可发的消息（postMessage）

| type | 载荷 | 效果 |
| :--- | :--- | :--- |
| `UPDATE_PARAM` | `{key, value}` | 改参数并触发 `reset()` |
| `HIGHLIGHT_TARGET` | `{key, active}` | 高亮某个物理量（画准星） |
| `RESET` | — | 重置 |
| `GHOST_TOGGLE` | — | 冻结 / 清除残影 |

## 坑

1. **别在 `<head>` 里自己写 `window.onerror`**：底座已经做了，重复会互相覆盖，自愈链路就断了。
2. **别用 `<canvas>` 画主体**：四层拆解、残影、靶向都依赖 SVG 节点。
3. **`reset()` 里要重画 L0**：参数变了，刻度/轨道往往要跟着变。
4. **首帧别假设 DOM 已就绪**：底座把首次 `reset()` 推迟到第一帧，那之前不要读 DOM。
5. **性能**：`HOLO.L*()` 会做内容比较，但生成字符串仍然花时间；把重活放 `reset()`，`frame()` 里只拼变化的部分。