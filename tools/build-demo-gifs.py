# -*- coding: utf-8 -*-
"""把 assets/_interactions/ 里的交互帧合成三张演示 GIF。

- assets/demo-01-slider.gif    拖滑块：谐波项数 1 → 25
- assets/demo-02-selfheal.gif  沙盒报错 → 自愈 → 重渲染
- assets/demo-03-split.gif     生成 → A/B 同屏对比

用法：
    node tools/capture-interactions.mjs     # 先截帧
    python tools/build-demo-gifs.py
"""
import glob
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "_interactions")
ASSETS = os.path.join(ROOT, "assets")

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]

SPECS = [
    {
        "slug": "slider",
        "out": "demo-01-slider.gif",
        "caption": "拖滑块：谐波项数 1 → 25，方波被一点点拼出来",
        "duration": 130,
        "width": 900,
    },
    {
        "slug": "selfheal",
        "out": "demo-02-selfheal.gif",
        "caption": "沙盒报错 → Self-Healing Agent 自动修复 → 重渲染",
        "duration": 560,
        "dedupe": True,
        "width": 900,
    },
    {
        "slug": "split",
        "out": "demo-03-split.gif",
        "caption": "一句话生成 → A/B 同屏对比，两边各自独立调参",
        "duration": 420,
        "width": 900,
    },
]


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def decorate(im, caption, font):
    """底部压一条半透明说明条，让 GIF 自己会说话。"""
    w, h = im.size
    bar = 46
    canvas = Image.new("RGB", (w, h + bar), (8, 13, 24))
    canvas.paste(im, (0, 0))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, h, w, h + bar], fill=(8, 13, 24))
    d.text((18, h + 12), caption, fill=(148, 190, 230), font=font)
    return canvas


def dedupe(frames, threshold=0.28):
    """去掉几乎一样的相邻帧。只在"要等十几秒"的自愈场景用——
    缩略图对比对细微的曲线变化不敏感，短序列直接全留，否则会把动画抽成 PPT。"""
    kept = [frames[0]]
    for im in frames[1:]:
        a = kept[-1].convert("L").resize((96, 60))
        b = im.convert("L").resize((96, 60))
        diff = sum(abs(x - y) for x, y in zip(a.tobytes(), b.tobytes())) / (96 * 60)
        if diff > threshold:
            kept.append(im)
    return kept


def build(spec):
    files = sorted(glob.glob(os.path.join(SRC, f"{spec['slug']}-*.png")))
    if not files:
        print(f"  跳过 {spec['slug']}：没找到帧")
        return
    font = load_font(17)
    frames = []
    for f in files:
        im = Image.open(f).convert("RGB")
        w = spec["width"]
        h = round(im.height * w / im.width)
        frames.append(im.resize((w, h), Image.LANCZOS))

    before = len(frames)
    if spec.get("dedupe"):
        frames = dedupe(frames)
    frames = [decorate(im, spec["caption"], font).convert("P", palette=Image.ADAPTIVE, colors=64) for im in frames]

    out = os.path.join(ASSETS, spec["out"])
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=spec["duration"],
        loop=0,
        optimize=True,
        disposal=2,
    )
    size = os.path.getsize(out) / 1024
    print(f"  {spec['out']}  {len(frames)} 帧（去重前 {before}）  {size:.0f} KB")


def main():
    print("合成交互 GIF：")
    for spec in SPECS:
        build(spec)


if __name__ == "__main__":
    main()