#!/usr/bin/env python3
"""生成带「2」徽章的微信双开图标。

用法:
    make_icon.py <源 icns 或 png> <输出 iconset 目录>

示例:
    make_icon.py /Applications/WeChat.app/Contents/Resources/AppIcon.icns ./icon.iconset
    iconutil -c icns ./icon.iconset -o AppIcon2.icns

仅依赖 Pillow（PIL）。
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = 4  # 超采样倍数


def load_source(path):
    """读取源图；icns 先用 sips 转 png。"""
    if path.lower().endswith(".icns"):
        tmp = os.path.join(tempfile.mkdtemp(prefix="wxicon-"), "base.png")
        subprocess.run(
            ["sips", "-s", "format", "png", path, "--out", tmp],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        path = tmp
    return Image.open(path).convert("RGBA")


def draw_badge(base):
    W, H = base.size
    big = base.resize((W * S, H * S), Image.LANCZOS)
    d = ImageDraw.Draw(big, "RGBA")

    cx, cy = int(W * S * 0.805), int(H * S * 0.805)  # 徽章中心：右下
    r_outer = int(W * S * 0.205)                     # 含白描边的半径
    ring = int(W * S * 0.022)                        # 白描边宽度

    # 1) 投影
    shadow = Image.new("RGBA", big.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    off = int(W * S * 0.008)
    sd.ellipse([cx - r_outer + off, cy - r_outer + off,
                cx + r_outer + off, cy + r_outer + off], fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(int(W * S * 0.014)))
    big = Image.alpha_composite(big, shadow)
    d = ImageDraw.Draw(big, "RGBA")

    # 2) 白色描边底圈
    d.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
              fill=(255, 255, 255, 255))

    # 3) 橙色渐变圆（自上而下）
    r_in = r_outer - ring
    grad = Image.new("RGBA", (2 * r_in, 2 * r_in), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    top, bot = (255, 165, 0), (255, 90, 0)          # 橙 -> 橘红
    for y in range(2 * r_in):
        t = y / max(1, 2 * r_in - 1)
        col = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,)
        gd.line([(0, y), (2 * r_in, y)], fill=col)
    mask = Image.new("L", (2 * r_in, 2 * r_in), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 2 * r_in - 1, 2 * r_in - 1], fill=255)
    big.paste(grad, (cx - r_in, cy - r_in), mask)

    # 4) 数字 2
    font_path = "/System/Library/Fonts/SFNSRounded.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    font = ImageFont.truetype(font_path, int(r_in * 1.52))
    txt = "2"
    bbox = d.textbbox((0, 0), txt, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = cx - tw / 2 - bbox[0]
    ty = cy - th / 2 - bbox[1] - int(r_in * 0.02)
    d.text((tx + int(r_in * 0.012), ty + int(r_in * 0.012)), txt,
           font=font, fill=(0, 0, 0, 60))          # 轻微内阴影
    d.text((tx, ty), txt, font=font, fill=(255, 255, 255, 255))

    return big.resize((W, H), Image.LANCZOS)


def main():
    if len(sys.argv) != 3:
        print("用法: make_icon.py <源 icns 或 png> <输出 iconset 目录>", file=sys.stderr)
        return 2

    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)

    icon = draw_badge(load_source(src))

    specs = [(16, "16x16"), (32, "16x16@2x"), (32, "32x32"), (64, "32x32@2x"),
             (128, "128x128"), (256, "128x128@2x"), (256, "256x256"),
             (512, "256x256@2x"), (512, "512x512"), (1024, "512x512@2x")]
    for px, name in specs:
        icon.resize((px, px), Image.LANCZOS).save(os.path.join(out, f"icon_{name}.png"))

    print(f"iconset 已生成: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
