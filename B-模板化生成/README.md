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
│   ├── oscillator.py       阻尼单摆
│   └── projectile.py       抛体运动（含空气阻力）
├── examples/
│   ├── plan-oscillator.json
│   └── plan-projectile.json
└── out/                    渲染产物（git 忽略）
```

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
| 必须留 `#btnPause` / `#btnReset` | 外壳不生成按钮，由模板负责（见现有模板） |

---

## 为什么这不只是"更快"

1. **可测试**：模板是普通 Python 函数，可以断言"45° 无阻力时射程 = v²/g"。
2. **可审计**：模型输出的 JSON 只有几个数字，人能一眼看完，不会偷偷塞进错误公式。
3. **可离线**：`--plan` 模式完全不调模型，教学场景可以预置一整套实验。
4. **成本**：一次生成的成本约为 A 的 1/15。

代价也很清楚：**用户问"量子隧穿"时，模板库里没有，只能选最接近的并标注"近似"**——这正是 A 存在的意义。

---

## 建议：混合路由（v0.2 的落点）

```
用户输入
   │
   ├─► 先问模型「这属于哪个模板？」── 命中且置信 ──► B 渲染（4 秒，稳）
   │
   └─► 未命中 ──► 回落到 A 的双 Agent（30 秒，任意概念）
```

这样 80% 的常见概念走 4 秒快路径，长尾概念仍有兜底，且兜底失败时用户已经习惯了等待。

实现上只需要一个路由函数 + A 的 `/api/generate` 作为 fallback，`generator.py` 的 `plan_from_text` 已经能判断"是否命中"（模板名是否在注册表里）。