#!/usr/bin/env python3
"""Generate crisp 24-bit ANSI TrueColor Unicode Braille logo from nox-logo-transparente.png."""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance

# Unicode Braille dot bit positions for (dx in {0,1}, dy in {0,1,2,3}):
# (0,0)=0x01, (0,1)=0x02, (0,2)=0x04, (1,0)=0x08, (1,1)=0x10, (1,2)=0x20, (0,3)=0x40, (1,3)=0x80
DOT_MASK = {
    (0, 0): 0x01,
    (0, 1): 0x02,
    (0, 2): 0x04,
    (0, 3): 0x40,
    (1, 0): 0x08,
    (1, 1): 0x10,
    (1, 2): 0x20,
    (1, 3): 0x80,
}


def generate_braille_logo(src_png: Path, cols: int = 30) -> str:
    img = Image.open(src_png).convert("RGBA")
    # Crop strictly around non-transparent pixels with tight margin, focusing on recognizable core (Omega + Lambda)
    alpha = np.array(img)[:, :, 3]
    ys, xs = np.where(alpha > 20)
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    # Trim outer dashed rings so Omega + Lambda + crescent gems stay super crisp at ~28-30 chars
    w_box, h_box = x1 - x0, y1 - y0
    trim_x = int(w_box * 0.125)
    trim_y = int(h_box * 0.11)
    crop = img.crop((x0 + trim_x, y0 + trim_y, x1 - trim_x, y1 - trim_y))

    # Boost saturation slightly and preserve deep violet tones cleanly in Braille cells
    rgb_img = ImageEnhance.Color(crop).enhance(1.22)
    rgb_img = ImageEnhance.Brightness(rgb_img).enhance(1.06)

    pw = cols * 2
    # Terminal char aspect ~ 1:2, Braille cell is 2x4 dots -> square visual aspect matches pw x ph!
    aspect = crop.height / crop.width
    rows = max(8, round((pw * aspect) / 4.0))
    ph = rows * 4

    resized = rgb_img.resize((pw, ph), Image.Resampling.LANCZOS)
    arr = np.array(resized, dtype=np.float32)

    lines: list[str] = []
    for r in range(rows):
        row_chars: list[str] = []
        last_rgb = None
        for c in range(cols):
            mask = 0
            r_sum = g_sum = b_sum = w_sum = 0.0
            for dy in range(4):
                for dx in range(2):
                    py = r * 4 + dy
                    px = c * 2 + dx
                    cr, cg, cb, ca = arr[py, px]
                    luma = 0.2126 * cr + 0.7152 * cg + 0.0722 * cb
                    max_c = max(cr, cg, cb)
                    # Keep deep violet Lambda cells solid (alpha-first + max channel), preserve real inner cutout gaps
                    if ca > 72 and (max_c > 36 or luma > 10):
                        mask |= DOT_MASK[(dx, dy)]
                        wt = ca / 255.0
                        r_sum += cr * wt
                        g_sum += cg * wt
                        b_sum += cb * wt
                        w_sum += wt
            if mask == 0:
                if last_rgb is not None:
                    row_chars.append("\x1b[0m ")
                    last_rgb = None
                else:
                    row_chars.append(" ")
            else:
                ar = int(min(255, max(0, round(r_sum / w_sum))))
                ag = int(min(255, max(0, round(g_sum / w_sum))))
                ab = int(min(255, max(0, round(b_sum / w_sum))))
                rgb = (ar, ag, ab)
                ch = chr(0x2800 + mask)
                if rgb != last_rgb:
                    row_chars.append(f"\x1b[38;2;{ar};{ag};{ab}m{ch}")
                    last_rgb = rgb
                else:
                    row_chars.append(ch)
        if last_rgb is not None:
            row_chars.append("\x1b[0m")
        lines.append("".join(row_chars))
    # Strip trailing completely blank lines (preserving fixed col width on non-empty lines)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cols", type=int, default=28)
    args = ap.parse_args()
    txt = generate_braille_logo(args.src, cols=args.cols)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(txt, encoding="utf-8")
    print(f"Generated Braille logo ({args.cols} cols, {len(txt.splitlines())} lines) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
