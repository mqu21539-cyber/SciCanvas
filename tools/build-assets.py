# -*- coding: utf-8 -*-
"""把截好的帧合成为 README 素材：assets/demo.gif + assets/social-preview.png。

依赖 Pillow（DSH 自带环境即可）。
用法：python tools/build-assets.py
"""
import glob
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = os.path.join(ROOT, "assets", "_frames")
ASSETS = os.path.join(ROOT, "assets")

ORDER = ["lorenz", "wave", "efield", "orbit", "projectile", "doppler"]


def load_frames():
    paths = []
    for name in ORDER:
        paths.extend(sorted(glob.glob(os.path.join(FRAMES, f"{name}-*.png"))))
    if not paths:
        raise SystemExit(f"没找到帧：{FRAMES}（先跑 node tools/capture-frames.mjs）")
    return paths


def build_gif():
    files = load_frames()
    imgs = []
    for f in files:
        im = Image.open(f).convert("RGB")
        w = 880
        h = round(im.height * w / im.width)
        imgs.append(im.resize((w, h), Image.LANCZOS))

    # 每帧 90ms ≈ 11fps；同一实验的 3 帧连起来有"在动"的感觉。
    # 全息底座有大量渐变与发光，128 色会撑到 4.7MB，64 色能压到 2MB 出头且肉眼几乎无差。
    out = os.path.join(ASSETS, "demo.gif")
    frames = [im.convert("P", palette=Image.ADAPTIVE, colors=64) for im in imgs]
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=90,
        loop=0,
        optimize=True,
        disposal=2,
    )
    size_mb = os.path.getsize(out) / 1024 / 1024
    print(f"demo.gif  {len(frames)} 帧  {size_mb:.2f} MB")
    return size_mb


def font(size, bold=True):
    for cand in (
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
    ):
        if os.path.exists(cand):
            return ImageFont.truetype(cand, size)
    return ImageFont.load_default()


def build_social():
    W, H = 1280, 640
    img = Image.new("RGB", (W, H), (11, 18, 32))
    d = ImageDraw.Draw(img)

    # 背景渐变
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(11 + 4 * t), int(18 + 5 * t), int(32 + 10 * t)))

    # 装饰正弦波
    for k, (amp, alpha, col) in enumerate([(46, 40, (56, 189, 248)), (30, 30, (168, 85, 247))]):
        pts = []
        for x in range(0, W, 4):
            y = H - 90 + amp * math.sin(x / 130 + k * 1.7)
            pts.append((x, y))
        d.line(pts, fill=col, width=2)

    # 左侧文案
    d.text((64, 150), "SciCanvas", font=font(76), fill=(241, 245, 249))
    d.text((68, 250), "Textbook concept  ->  interactive 2D lab", font=font(28, False), fill=(148, 163, 184))
    d.text((68, 292), "Dual-Agent  ·  Self-healing sandbox  ·  dsh plugin", font=font(22, False), fill=(100, 116, 139))

    chips = [("MIT", (34, 197, 94)), ("DeepSeek", (77, 107, 254)), ("dsh", (56, 189, 248))]
    x = 68
    for label, col in chips:
        tw = d.textlength(label, font=font(18, False))
        d.rounded_rectangle([x, 356, x + tw + 28, 392], radius=8, outline=col, width=2)
        d.text((x + 14, 362), label, font=font(18, False), fill=col)
        x += tw + 44

    # 右侧实验室截图
    shot_path = os.path.join(FRAMES, "lorenz-1.png")
    if os.path.exists(shot_path):
        shot = Image.open(shot_path).convert("RGB")
        sw, sh = 620, 388
        shot = shot.resize((sw, sh), Image.LANCZOS)
        px, py = W - sw - 64, (H - sh) // 2
        d.rounded_rectangle([px - 8, py - 8, px + sw + 8, py + sh + 8], radius=16, fill=(15, 23, 42), outline=(30, 41, 59), width=2)
        img.paste(shot, (px, py))

    out = os.path.join(ASSETS, "social-preview.png")
    img.save(out, optimize=True)
    print(f"social-preview.png  1280x640  {os.path.getsize(out) / 1024:.0f} KB")


if __name__ == "__main__":
    if not os.path.isdir(FRAMES):
        sys.exit(f"缺 {FRAMES}")
    mb = build_gif()
    build_social()
    if mb > 10:
        print("⚠️ demo.gif 超过 10MB，把 FRAME_W 调小后重新截帧")