# B · 模板化生成（原型）

> 与 `A-自由生成` 并列的第二条技术路线。
> **A 负责"什么都能试"，B 负责"每次都对"。**

---

## 一句话原理

不让模型写 HTML，只让它**从模板库里挑一个，并填参数**：

```
用户输入 ──► 模型只输出 300–500 tokens 的 JSON ──► 模板渲染 → 单文件 HTML
                 {"template": "projectile", "params": {"k": 0.3}, "title": …}
```

对比 A 方案让模型直接写 500–700 行代码，`token` 量下降一个数量级，且**物理正确性由模板作者保证，模型编不出错误公式**。

---

## 实测（同一台机器，同一个 Key，2026-11-05）

| | A · 自由生成 | B · 模板化 |
| :--- | :--- | :--- |
| 模型输出 tokens | 约 6,900 | **96** |
| 输入 tokens | 约 1,400 | **405** |
| 端到端耗时 | 24.8–30.0 s | **3.8 s** |
| 产物体积 | 600–700 行 | 约 250 行（模板复用） |
| 物理正确性 | 需抽检 | 模板固定，必然正确 |
| 覆盖范围 | 任意概念 | 仅已建模板 |

> 3.8 秒里还包含 Python 启动和 JSON 解析，模型调用本身约 2–3 秒。

---

## 目录

```
B-模板化生成/
├── generator.py            外壳 + 渲染 + 模型选模板 + CLI
├── templates/
│   ├── __init__.py         模板注册表 + 控件/指标 HTML 生成
│   ├── oscillator.py       阻尼单摆（振动）
│   ├── projectile.py       抛体运动（含空气阻力）
│   ├── wave.py             行波叠加与驻波
│   ├── efield.py           双点电荷电场线
│   ├── orbit.py            中心力场轨道（开普勒）
│   ├── lorenz.py           洛伦兹吸引子（混沌）
│   ├── fourier.py          傅里叶级数合成方波
│   ├── rc.py               RC 充放电
│   ├── heat.py             一维热传导
│   └── montecarlo.py       蒙特卡洛估 π
├── examples/
│   ├── plan-oscillator.json
│   └── plan-projectile.json
└── out/                    渲染产物（git 忽略）
```

## 模板清单

| name | 学科 | 核心模型 | 参数 |
| :--- | :--- | :--- | :--- |
| `oscillator` | 经典力学/振动 | `θ'' = −(g/L)sinθ − cθ'` | 摆长 L、阻尼 c、重力 g |
| `projectile` | 经典力学/运动学 | `a = −k·v − g·ŷ` | 初速 v₀、发射角 α、阻力 k |
| `wave` | 波动学 | `y = sin(kx−ωt) + sin(kx−ωt+φ)` | 波长 λ、波速 v、相位差 φ |
| `efield` | 电磁学 | `E = kq/r²`，场线积分 | q₁、q₂、间距 d |
| `orbit` | 天体物理 | `a = −μr̂/r²`，速度 Verlet | μ、r₀、速度倍率 |
| `lorenz` | 混沌 | `ẋ=σ(y−x)` 等，RK4 | σ、ρ、β、初始偏差 ε |
| `fourier` | 数学/信号 | 奇次谐波部分和 `(4/π)Σ sin(mωt)/m` | 项数 n、ω、初相 φ |
| `rc` | 电路 | `Vc = V₀(1−e^{−t/τ})`，τ=RC | R、C、V₀ |
| `heat` | 热学/偏微分 | `∂u/∂t = α∂²u/∂x²`，显式差分（r=0.4） | α、热区宽度、时间加速 |
| `montecarlo` | 概率/数值 | 撒点比例 × 4 估 π | 撒点速率、点大小 |

十者都在真实 Chrome 里验证过：**无 JS 异常、canvas 实际绘制、滑块注入正常**。

---

## 用法

```bash
cd B-模板化生成

# 1. 看有哪些模板和参数区间
python generator.py --list

# 2. 用手写的 plan 渲染（不花 token，纯本地）
python generator.py --plan examples/plan-oscillator.json --out out/osc.html

# 3. 直接指定模板 + 覆盖参数
python generator.py --template projectile --params "v0=40,ang=60,k=0.15" --out out/p.html

# 4. 自然语言 → 模型选模板（需 DEEPSEEK_API_KEY）
python generator.py --text "为什么有空气阻力时最佳发射角小于 45 度" --out out/a.html
```

模型 Key 的读取顺序：环境变量 `DEEPSEEK_API_KEY` → 本目录 `.env`。

---

## 加一个新模板（约 30 分钟）

新建 `templates/xxx.py`，只需暴露两个东西：

```python
META = {
    "name": "xxx",                       # CLI 与 plan 里用的 id
    "title": "默认标题",
    "category": "学科 / 子类",
    "formula": "核心公式（纯文本）",
    "controls": [                        # 参数区间即模型的填写范围
        {"id": "m", "label": "质量", "unit": "kg",
         "min": 0.1, "max": 10, "step": 0.1, "default": 1.0},
    ],
    "metrics": [                         # 实时指标（可留空）
        {"id": "E", "label": "动能", "color": "text-cyan-400"},
    ],
}

def build(params, copy):
    """返回 body 内部 HTML（含 canvas、控件、<script>）。"""
```

然后在 `templates/__init__.py` 的 `MODULES` 里加一行即可。

**模板契约（必须遵守，否则交互会坏）**

| 约束 | 原因 |
| :--- | :--- |
| 控件 input 的 `id` 必须等于 `controls[].id` | 外壳按 id 注入 `window.__SCICANVAS__` |
| 指标元素 `id` 必须是 `m_<metrics[].id>` | 模板按 id 写数值 |
| 数值显示 span 的 `id` 必须是 `val_<id>` | 拖动时刷新读数 |
| 必须用 `requestAnimationFrame` 且按固定步长积分 | 不同刷新率下轨迹一致 |
| 按钮由模板自己写（`#btnPause` / `#btnReset` 是约定，非强制） | 静态模板（如电场）不需要暂停 |

## 混合路由（已接进 A 的后端）

`A-自由生成/backend/router.py` 实现了「模板优先、Agent 兜底」：

```
用户输入 ──► 分诊（~1s）──命中──► B 渲染（立即）──► 总耗时约 1.3s
                  └────未命中────► A 双 Agent ────► 总耗时约 20–27s
```

实测四例：

| 输入 | 路由 | 耗时 |
| :--- | :--- | :--- |
| 单摆阻尼振动 | `template/oscillator`（置信度 0.98） | **1.3 s** |
| 抛体 + 空气阻力 | `template/projectile`（0.98） | **1.6 s** |
| 傅里叶级数合成方波 | `agent`（无对应模板） | 19.7 s |
| 单摆（强制 `strategy=agent`） | `agent` | 22.3 s |

前端顶部会显示徽标：`模板 · oscillator · 1.3s` 或 `双 Agent · 19.7s`。

---

## 为什么这不只是"更快"

1. **可测试**：模板是普通 Python 函数，可以断言"45° 无阻力时射程 = v²/g"。
2. **可审计**：模型输出的 JSON 只有几个数字，人能一眼看完，不会偷偷塞进错误公式。
3. **可离线**：`--plan` 模式完全不调模型，教学场景可以预置一整套实验。
4. **成本**：一次生成的成本约为 A 的 1/15。

代价也很清楚：**用户问"量子隧穿"时，模板库里没有，只能选最接近的并标注"近似"**——这正是 A 存在的意义。

---

## 建议：混合路由（已落地，见上）

```
用户输入
   │
   ├─► 先问模型「这属于哪个模板？」── 命中且置信 ──► B 渲染（约 4 秒，稳）
   │
   └─► 未命中 ──► 回落到 A 的双 Agent（30 秒，任意概念）
```

实现位置：`A-自由生成/backend/router.py`（`strategy=auto|template|agent`）。
分诊 prompt 的判定标准是**从严**的：只有核心物理模型一致才算命中，避免"看起来相关"的误判。