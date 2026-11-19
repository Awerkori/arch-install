#!/usr/bin/env python3
"""Deterministic Project Nox Obsidian Purple visual asset generator (4K masters, 60fps WebM, 50fps GIF)."""
from __future__ import annotations

import argparse
import math
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cairo
import numpy as np
from PIL import Image

_G_EMBLEM_SURF: cairo.ImageSurface | None = None


def halton(index: int, base: int) -> float:
    result = 0.0
    f = 1.0 / base
    i = index
    while i > 0:
        result += f * (i % base)
        i //= base
        f /= base
    return result


def build_particles(count: int, seed_offset: int, x_min: float, x_max: float, y_min: float, y_max: float, scale: float) -> list[dict]:
    items = []
    tones = [
        (1.0, 1.0, 1.0),         # cosmic white
        (0.88, 0.85, 0.98),      # soft silver-lilac
        (0.77, 0.71, 0.99),      # #c4b5fd lavender
        (0.99, 0.75, 0.14),      # subtle #fbbf24 gold spark
    ]
    for idx in range(count):
        i = idx + 1 + seed_offset
        hx = halton(i + 3, 2)
        hy = halton(i + 5, 3)
        hd = halton(i + 7, 5)
        hs = halton(i + 11, 7)
        is_gold = (idx % 9 == 0)
        is_mid = (idx % 3 == 0)
        r = (2.8 + hd * 1.9 if is_mid else 1.5 + hd * 1.4) * scale
        max_op = (0.42 + hd * 0.28) if is_mid else (0.22 + hd * 0.24)
        fall = (120 + hd * 140) * scale
        sway = (5 + hs * 10) * scale
        rgb = tones[3] if is_gold else tones[idx % 3]
        items.append(
            {
                "x": x_min + hx * (x_max - x_min),
                "y": y_min + hy * (y_max - y_min),
                "r": r,
                "max_op": max_op,
                "fall": fall,
                "sway": sway,
                "phase": idx / count,
                "sway_phase": hs,
                "rgb": rgb,
            }
        )
    return items


def pil_to_cairo_surface(img: Image.Image) -> cairo.ImageSurface:
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.uint8)
    # Cairo ARGB32 on little-endian is BGRA in memory, premultiplied!
    a = arr[:, :, 3:4].astype(np.float32) / 255.0
    bgra = np.empty_like(arr)
    bgra[:, :, 0] = np.clip(arr[:, :, 2] * a[:, :, 0], 0, 255).astype(np.uint8)
    bgra[:, :, 1] = np.clip(arr[:, :, 1] * a[:, :, 0], 0, 255).astype(np.uint8)
    bgra[:, :, 2] = np.clip(arr[:, :, 0] * a[:, :, 0], 0, 255).astype(np.uint8)
    bgra[:, :, 3] = arr[:, :, 3]
    h, w = bgra.shape[:2]
    buf = bytearray(bgra.tobytes())
    return cairo.ImageSurface.create_for_data(buf, cairo.FORMAT_ARGB32, w, h, w * 4)


def draw_cosmic_background(ctx: cairo.Context, w: int, h: int, glow_cx: float, glow_cy: float, ambient_scale: float = 1.0) -> None:
    bg = cairo.LinearGradient(0, 0, w, h)
    bg.add_color_stop_rgb(0.0, 0x09 / 255, 0x06 / 255, 0x10 / 255)
    bg.add_color_stop_rgb(0.48, 0x12 / 255, 0x0A / 255, 0x1F / 255)
    bg.add_color_stop_rgb(1.0, 0x08 / 255, 0x05 / 255, 0x0E / 255)
    ctx.set_source(bg)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    # Right atmospheric purple nebula
    r_amb = max(w, h) * 0.62
    g1 = cairo.RadialGradient(w * 0.86, h * 0.26, 0, w * 0.86, h * 0.26, r_amb)
    g1.add_color_stop_rgba(0.0, 0x7C / 255, 0x3A / 255, 0xED / 255, 0.16 * ambient_scale)
    g1.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
    ctx.set_source(g1)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    # Lower deep indigo/violet fill
    g2 = cairo.RadialGradient(w * 0.25, h * 0.85, 0, w * 0.25, h * 0.85, max(w, h) * 0.55)
    g2.add_color_stop_rgba(0.0, 0x4C / 255, 0x1D / 255, 0x95 / 255, 0.14 * ambient_scale)
    g2.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
    ctx.set_source(g2)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    # Subtle radial vignette anchored gently around focal zone
    vig = cairo.RadialGradient(glow_cx, glow_cy, min(w, h) * 0.22, w * 0.5, h * 0.5, math.hypot(w, h) * 0.56)
    vig.add_color_stop_rgba(0.0, 0.02, 0.01, 0.04, 0.0)
    vig.add_color_stop_rgba(1.0, 0.02, 0.01, 0.04, 0.48)
    ctx.set_source(vig)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()


def draw_particles(ctx: cairo.Context, particles: list[dict], p: float, wrap_h: float) -> None:
    for sp in particles:
        age = (p + sp["phase"]) % 1.0
        x = sp["x"] + sp["sway"] * math.sin(2 * math.pi * (p + sp["sway_phase"]))
        y = (sp["y"] + sp["fall"] * age) % wrap_h
        op = sp["max_op"] * math.sin(math.pi * age)
        if op <= 0.01:
            continue
        r, g, b = sp["rgb"]
        rad = sp["r"]
        grad = cairo.RadialGradient(x, y, 0, x, y, rad * 2.2)
        grad.add_color_stop_rgba(0.0, r, g, b, op)
        grad.add_color_stop_rgba(0.38, r, g, b, op * 0.45)
        grad.add_color_stop_rgba(1.0, r, g, b, 0.0)
        ctx.set_source(grad)
        ctx.arc(x, y, rad * 2.2, 0, 2 * math.pi)
        ctx.fill()


def draw_emblem_orbital_assembly(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    emblem_diam: float,
    p: float,
    emblem_surf: cairo.ImageSurface,
    draw_glows: bool = True,
) -> None:
    breath = 0.5 - 0.5 * math.cos(2 * math.pi * p)
    aurora_scale = 0.985 + 0.045 * breath
    aurora_op = 0.80 + 0.20 * breath

    r_inner = emblem_diam * 0.503
    r_outer = emblem_diam * 0.588

    if draw_glows:
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(aurora_scale, aurora_scale)
        neb_r = emblem_diam * 0.86
        neb = cairo.RadialGradient(0, 0, 0, 0, 0, neb_r)
        neb.add_color_stop_rgba(0.0, 0x93 / 255, 0x33 / 255, 0xEA / 255, 0.44 * aurora_op)
        neb.add_color_stop_rgba(0.50, 0x58 / 255, 0x1C / 255, 0x87 / 255, 0.20 * aurora_op)
        neb.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
        ctx.set_source(neb)
        ctx.arc(0, 0, neb_r, 0, 2 * math.pi)
        ctx.fill()

        gold_r = emblem_diam * 0.58
        gcore = cairo.RadialGradient(0, 0, 0, 0, 0, gold_r)
        gcore.add_color_stop_rgba(0.0, 0xFB / 255, 0xBF / 255, 0x24 / 255, 0.24 * aurora_op)
        gcore.add_color_stop_rgba(0.58, 0xD9 / 255, 0x77 / 255, 0x06 / 255, 0.08 * aurora_op)
        gcore.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
        ctx.set_source(gcore)
        ctx.arc(0, 0, gold_r, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

    # Outer dashed orbit (+180° aligned cleanly with dash period 30/360)
    unit_outer = (2 * math.pi * r_outer) / 360.0
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(math.radians(180.0 * p))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_dash([15 * unit_outer, 6 * unit_outer, 4 * unit_outer, 5 * unit_outer])
    # Soft glow pass
    ctx.set_line_width(emblem_diam * 0.017)
    ctx.set_source_rgba(0xA8 / 255, 0x55 / 255, 0xF7 / 255, 0.22)
    ctx.arc(0, 0, r_outer, 0, 2 * math.pi)
    ctx.stroke()
    # Core stroke pass with gradient
    og = cairo.LinearGradient(-r_outer, -r_outer, r_outer, r_outer)
    og.add_color_stop_rgba(0.0, 0xFB / 255, 0xBF / 255, 0x24 / 255, 0.94)
    og.add_color_stop_rgba(0.5, 0xA8 / 255, 0x55 / 255, 0xF7 / 255, 0.48)
    og.add_color_stop_rgba(1.0, 0xF5 / 255, 0x9E / 255, 0x0B / 255, 0.94)
    ctx.set_source(og)
    ctx.set_line_width(emblem_diam * 0.0115)
    ctx.arc(0, 0, r_outer, 0, 2 * math.pi)
    ctx.stroke()
    ctx.restore()

    # Inner dashed orbit (-420° aligned cleanly with dash period 15/360: 420/15=28!)
    unit_inner = (2 * math.pi * r_inner) / 360.0
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(math.radians(-420.0 * p))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_dash([8 * unit_inner, 7 * unit_inner])
    ctx.set_line_width(emblem_diam * 0.014)
    ctx.set_source_rgba(0xB9 / 255, 0x73 / 255, 0xFA / 255, 0.18)
    ctx.arc(0, 0, r_inner, 0, 2 * math.pi)
    ctx.stroke()
    ctx.set_line_width(emblem_diam * 0.0088)
    ctx.set_source_rgba(0xB9 / 255, 0x73 / 255, 0xFA / 255, 0.80)
    ctx.arc(0, 0, r_inner, 0, 2 * math.pi)
    ctx.stroke()
    ctx.restore()

    # Crisp emblem raster (emblema-mestre-1254)
    src_w = emblem_surf.get_width()
    scale_e = emblem_diam / src_w
    ctx.save()
    ctx.translate(cx - emblem_diam / 2, cy - emblem_diam / 2)
    ctx.scale(scale_e, scale_e)
    pat = cairo.SurfacePattern(emblem_surf)
    pat.set_filter(cairo.FILTER_BEST)
    ctx.set_source(pat)
    ctx.paint()
    ctx.restore()

    # Outer golden orb satellite (+360° per loop)
    ang_gold = math.radians(360.0 * p - 90.0)
    gx = cx + r_outer * math.cos(ang_gold)
    gy = cy + r_outer * math.sin(ang_gold)
    gr_halo = emblem_diam * 0.048
    gh = cairo.RadialGradient(gx, gy, 0, gx, gy, gr_halo)
    gh.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.96)
    gh.add_color_stop_rgba(0.28, 0xFE / 255, 0xF0 / 255, 0x8A / 255, 0.88)
    gh.add_color_stop_rgba(0.60, 0xFB / 255, 0xBF / 255, 0x24 / 255, 0.35)
    gh.add_color_stop_rgba(1.0, 0xFB / 255, 0xBF / 255, 0x24 / 255, 0.0)
    ctx.set_source(gh)
    ctx.arc(gx, gy, gr_halo, 0, 2 * math.pi)
    ctx.fill()

    # Inner magenta orb satellite (-360° per loop)
    ang_mag = math.radians(-360.0 * p + 90.0)
    mx = cx + r_inner * math.cos(ang_mag)
    my = cy + r_inner * math.sin(ang_mag)
    mr_halo = emblem_diam * 0.038
    mh = cairo.RadialGradient(mx, my, 0, mx, my, mr_halo)
    mh.add_color_stop_rgba(0.0, 1.0, 0.97, 1.0, 0.95)
    mh.add_color_stop_rgba(0.30, 0xD9 / 255, 0x46 / 255, 0xEF / 255, 0.84)
    mh.add_color_stop_rgba(0.62, 0xA8 / 255, 0x55 / 255, 0xF7 / 255, 0.30)
    mh.add_color_stop_rgba(1.0, 0xA8 / 255, 0x55 / 255, 0xF7 / 255, 0.0)
    ctx.set_source(mh)
    ctx.arc(mx, my, mr_halo, 0, 2 * math.pi)
    ctx.fill()


def draw_corner_brackets(ctx: cairo.Context, w: int, h: int, pad: float, arm: float, lw: float) -> None:
    ctx.save()
    ctx.set_line_width(lw)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for (x0, y0, dx, dy) in [
        (pad, pad, 1, 1),
        (w - pad, pad, -1, 1),
        (pad, h - pad, 1, -1),
        (w - pad, h - pad, -1, -1),
    ]:
        ctx.set_source_rgba(0x7C / 255, 0x3A / 255, 0xED / 255, 0.55)
        ctx.move_to(x0 + dx * arm, y0)
        ctx.line_to(x0, y0)
        ctx.line_to(x0, y0 + dy * arm)
        ctx.stroke()
        # Subtle gold corner node dot
        ctx.set_source_rgba(0xFB / 255, 0xBF / 255, 0x24 / 255, 0.85)
        ctx.arc(x0, y0, lw * 1.4, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()


def draw_thin_divider(ctx: cairo.Context, cx: float, y: float, width: float, thickness: float) -> None:
    x0 = cx - width / 2
    g = cairo.LinearGradient(x0, y, x0 + width, y)
    g.add_color_stop_rgba(0.0, 0x6B / 255, 0x21 / 255, 0xA8 / 255, 0.0)
    g.add_color_stop_rgba(0.25, 0x7C / 255, 0x3A / 255, 0xED / 255, 0.45)
    g.add_color_stop_rgba(0.50, 0xD9 / 255, 0x77 / 255, 0x06 / 255, 0.78)
    g.add_color_stop_rgba(0.75, 0x7C / 255, 0x3A / 255, 0xED / 255, 0.45)
    g.add_color_stop_rgba(1.0, 0x6B / 255, 0x21 / 255, 0xA8 / 255, 0.0)
    ctx.set_source(g)
    ctx.set_line_width(thickness)
    ctx.move_to(x0, y)
    ctx.line_to(x0 + width, y)
    ctx.stroke()
    ctx.set_source_rgba(0xFB / 255, 0xBF / 255, 0x24 / 255, 0.90)
    ctx.arc(cx, y, thickness * 1.6, 0, 2 * math.pi)
    ctx.fill()


def render_g5_frame(w: int, h: int, p: float, emblem_surf: cairo.ImageSurface, particles: list[dict]) -> bytes:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    cx, cy = w * 0.50, h * 0.515
    draw_cosmic_background(ctx, w, h, cx, cy, 1.0)

    # Very faint sweeping horizon cosmic ring arc across full width
    ctx.save()
    ctx.set_line_width(max(1.0, h * 0.0011))
    arc_g = cairo.LinearGradient(w * 0.12, cy, w * 0.88, cy)
    arc_g.add_color_stop_rgba(0.0, 0x6B / 255, 0x21 / 255, 0xA8 / 255, 0.0)
    arc_g.add_color_stop_rgba(0.28, 0x7C / 255, 0x3A / 255, 0xED / 255, 0.22)
    arc_g.add_color_stop_rgba(0.50, 0xFB / 255, 0xBF / 255, 0x24 / 255, 0.16)
    arc_g.add_color_stop_rgba(0.72, 0x7C / 255, 0x3A / 255, 0xED / 255, 0.22)
    arc_g.add_color_stop_rgba(1.0, 0x6B / 255, 0x21 / 255, 0xA8 / 255, 0.0)
    ctx.set_source(arc_g)
    ctx.move_to(w * 0.10, cy)
    ctx.line_to(w * 0.90, cy)
    ctx.stroke()
    ctx.restore()

    draw_particles(ctx, particles, p, float(h))
    draw_emblem_orbital_assembly(ctx, cx, cy, h * 0.36, p, emblem_surf, draw_glows=True)
    # Return raw RGB24 bytes for zero-copy pipe to ffmpeg or PIL
    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return rgb.tobytes()


def render_aoc_frame(w: int, h: int, p: float, emblem_surf: cairo.ImageSurface, particles: list[dict]) -> bytes:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    cx, cy = w * 0.50, h * 0.425
    draw_cosmic_background(ctx, w, h, cx, cy, 1.05)

    # Vertical cosmic spine & subtle elliptical filaments unique to portrait AOC monitor
    ctx.save()
    lw = max(1.2, w * 0.0014)
    spine = cairo.LinearGradient(cx, h * 0.08, cx, h * 0.91)
    spine.add_color_stop_rgba(0.0, 0x6B / 255, 0x21 / 255, 0xA8 / 255, 0.0)
    spine.add_color_stop_rgba(0.24, 0x7C / 255, 0x3A / 255, 0xED / 255, 0.35)
    spine.add_color_stop_rgba(0.45, 0xFB / 255, 0xBF / 255, 0x24 / 255, 0.28)
    spine.add_color_stop_rgba(0.75, 0x93 / 255, 0x33 / 255, 0xEA / 255, 0.38)
    spine.add_color_stop_rgba(1.0, 0x6B / 255, 0x21 / 255, 0xA8 / 255, 0.0)
    ctx.set_source(spine)
    ctx.set_line_width(lw)
    ctx.move_to(cx, h * 0.08)
    ctx.line_to(cx, h * 0.91)
    ctx.stroke()

    # Subtle vertical orbital resonance ellipses framing top-to-bottom composition
    pulse = 0.72 + 0.28 * (0.5 - 0.5 * math.cos(2 * math.pi * p))
    for rx, ry, al in [(w * 0.39, h * 0.36, 0.14 * pulse), (w * 0.44, h * 0.41, 0.09 * pulse)]:
        ctx.save()
        ctx.translate(cx, h * 0.48)
        ctx.scale(rx, ry)
        ctx.set_line_width(lw / min(rx, ry))
        ctx.set_source_rgba(0x93 / 255, 0x33 / 255, 0xEA / 255, al)
        ctx.arc(0, 0, 1.0, 0, 2 * math.pi)
        ctx.stroke()
        ctx.restore()

    # Constellation anchor nodes along lower spine
    for frac, rad_m, gold in [(0.70, 3.2, True), (0.76, 2.2, False), (0.83, 2.6, True), (0.15, 2.4, False)]:
        ny = h * frac
        node_r = rad_m * (w / 1080.0) * 2.2
        ng = cairo.RadialGradient(cx, ny, 0, cx, ny, node_r * 2.5)
        if gold:
            ng.add_color_stop_rgba(0.0, 0xFE / 255, 0xF0 / 255, 0x8A / 255, 0.9 * pulse)
            ng.add_color_stop_rgba(1.0, 0xFB / 255, 0xBF / 255, 0x24 / 255, 0.0)
        else:
            ng.add_color_stop_rgba(0.0, 0xE9 / 255, 0xD5 / 255, 0xFF / 255, 0.8 * pulse)
            ng.add_color_stop_rgba(1.0, 0x93 / 255, 0x33 / 255, 0xEA / 255, 0.0)
        ctx.set_source(ng)
        ctx.arc(cx, ny, node_r * 2.5, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()

    draw_particles(ctx, particles, p, float(h))
    draw_emblem_orbital_assembly(ctx, cx, cy, w * 0.43, p, emblem_surf, draw_glows=True)
    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return rgb.tobytes()


def render_sticker_frame(size: int, p: float, emblem_surf: cairo.ImageSurface) -> bytes:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surf)
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)
    draw_emblem_orbital_assembly(ctx, size * 0.5, size * 0.5, size * 0.72, p, emblem_surf, draw_glows=True)
    # Unpremultiply BGRA -> RGBA for transparent GIF export
    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((size, size, 4)).copy()
    rgba = arr[:, :, [2, 1, 0, 3]].astype(np.float32)
    a = rgba[:, :, 3:4]
    nz = a[:, :, 0] > 0
    for c in range(3):
        rgba[nz, c] = np.clip((rgba[nz, c] * 255.0) / a[nz, 0], 0, 255)
    return rgba.astype(np.uint8).tobytes()


def render_lockscreen_bg(w: int, h: int, emblem_surf: cairo.ImageSurface) -> Image.Image:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    # Center focal glow strictly near upper crest (y=0.18*H) so clock (0.39*H) & login box (0.68*H) stay crisp dark
    draw_cosmic_background(ctx, w, h, w * 0.50, h * 0.19, 0.85)
    parts = build_particles(42, 77, w * 0.04, w * 0.96, h * 0.03, h * 0.96, h / 1080.0)
    draw_particles(ctx, parts, 0.25, float(h))

    # Upper subtle nebula behind animated sticker zone (y=0.18*H)
    neb = cairo.RadialGradient(w * 0.50, h * 0.185, 0, w * 0.50, h * 0.185, h * 0.28)
    neb.add_color_stop_rgba(0.0, 0x93 / 255, 0x33 / 255, 0xEA / 255, 0.28)
    neb.add_color_stop_rgba(0.60, 0x58 / 255, 0x1C / 255, 0x87 / 255, 0.10)
    neb.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
    ctx.set_source(neb)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    # Architectural sanctuary frame around lock composition
    draw_corner_brackets(ctx, w, h, h * 0.045, h * 0.045, max(1.5, h * 0.0018))
    draw_thin_divider(ctx, w * 0.50, h * 0.495, w * 0.34, max(1.4, h * 0.0014))

    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return Image.fromarray(rgb, mode="RGB")


def render_greeter_bg(w: int, h: int) -> Image.Image:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    draw_cosmic_background(ctx, w, h, w * 0.50, h * 0.50, 0.85)
    parts = build_particles(40, 108, w * 0.04, w * 0.96, h * 0.04, h * 0.96, h / 1080.0)
    draw_particles(ctx, parts, 0.35, float(h))

    # Subtle outer cosmic sanctuary ring framing the central login box cleanly
    ctx.save()
    ctx.set_line_width(max(1.2, h * 0.0012))
    ctx.set_source_rgba(0x7C / 255, 0x3A / 255, 0xED / 255, 0.24)
    ctx.arc(w * 0.50, h * 0.50, h * 0.39, 0, 2 * math.pi)
    ctx.stroke()
    ctx.set_dash([h * 0.012, h * 0.010])
    ctx.set_source_rgba(0xFB / 255, 0xBF / 255, 0x24 / 255, 0.22)
    ctx.arc(w * 0.50, h * 0.50, h * 0.425, 0, 2 * math.pi)
    ctx.stroke()
    ctx.restore()

    draw_corner_brackets(ctx, w, h, h * 0.045, h * 0.045, max(1.5, h * 0.0018))
    draw_thin_divider(ctx, w * 0.50, h * 0.145, w * 0.42, max(1.4, h * 0.0014))

    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return Image.fromarray(rgb, mode="RGB")


def render_limine_bg(w: int, h: int, emblem_surf: cairo.ImageSurface) -> Image.Image:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    # Keep center dark & calm for Limine menu entries; anchor crest in upper-right safe corner
    draw_cosmic_background(ctx, w, h, w * 0.87, h * 0.18, 0.55)
    parts = build_particles(26, 202, w * 0.04, w * 0.96, h * 0.04, h * 0.96, h / 1080.0)
    draw_particles(ctx, parts, 0.18, float(h))

    draw_corner_brackets(ctx, w, h, h * 0.04, h * 0.042, max(1.5, h * 0.0018))
    # Subtle top-right emblem badge outside the menu text area
    draw_emblem_orbital_assembly(ctx, w * 0.875, h * 0.20, h * 0.175, 0.0, emblem_surf, draw_glows=True)
    # Subtle architectural separator rule near bottom
    draw_thin_divider(ctx, w * 0.50, h * 0.915, w * 0.52, max(1.2, h * 0.0013))

    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return Image.fromarray(rgb, mode="RGB")


def _worker_frame(task: tuple) -> tuple[int, bytes]:
    kind, idx, total, w, h, emblem_path, particles = task
    global _G_EMBLEM_SURF
    if _G_EMBLEM_SURF is None:
        _G_EMBLEM_SURF = pil_to_cairo_surface(Image.open(emblem_path))
    p = idx / total
    if kind == "g5":
        return idx, render_g5_frame(w, h, p, _G_EMBLEM_SURF, particles)
    if kind == "aoc":
        return idx, render_aoc_frame(w, h, p, _G_EMBLEM_SURF, particles)
    return idx, render_sticker_frame(w, p, _G_EMBLEM_SURF)


def encode_video_and_gif(kind: str, w: int, h: int, emblem_path: Path, particles: list[dict], webm_out: Path | None, gif_out: Path | None, workers: int) -> None:
    # Render 300 frames (50 FPS, 6.0s exact 20ms GIF timing) or 360 frames (60 FPS WebM)
    # Rendering 300 frames for GIF AND 360 frames for WebM in parallel raw pipes!
    if webm_out is not None:
        fps_w, n_w = 60, 360
        webm_out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{w}x{h}", "-r", str(fps_w), "-i", "-",
            "-c:v", "libvpx-vp9", "-crf", "16", "-b:v", "0", "-pix_fmt", "yuv420p",
            "-deadline", "good", "-cpu-used", "2", "-row-mt", "1", "-threads", str(workers),
            str(webm_out),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        assert proc.stdin is not None
        tasks = [(kind, i, n_w, w, h, str(emblem_path), particles) for i in range(n_w)]
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for _idx, raw in ex.map(_worker_frame, tasks, chunksize=8):
                proc.stdin.write(raw)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg webm failed: {proc.stderr.read().decode() if proc.stderr else rc}")

    if gif_out is not None:
        fps_g, n_g = 50, 300
        gif_out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpd:
            raw_mp4 = Path(tmpd) / "lossless.nut"
            if kind == "sticker":
                pix_in = "rgba"
                vf_pal = "palettegen=stats_mode=full:reserve_transparent=1"
                vf_use = "paletteuse=dither=floyd_steinberg"
            else:
                pix_in = "rgb24"
                vf_pal = "palettegen=stats_mode=full:reserve_transparent=0"
                vf_use = "paletteuse=dither=floyd_steinberg:diff_mode=rectangle"

            cmd_cap = [
                "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", pix_in,
                "-s", f"{w}x{h}", "-r", str(fps_g), "-i", "-",
                "-c:v", "rawvideo", "-pix_fmt", pix_in, str(raw_mp4),
            ]
            p1 = subprocess.Popen(cmd_cap, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            assert p1.stdin is not None
            tasks = [(kind, i, n_g, w, h, str(emblem_path), particles) for i in range(n_g)]
            with ProcessPoolExecutor(max_workers=workers) as ex:
                for _idx, raw in ex.map(_worker_frame, tasks, chunksize=8):
                    p1.stdin.write(raw)
            p1.stdin.close()
            rc1 = p1.wait()
            if rc1 != 0:
                raise RuntimeError(f"ffmpeg capture failed: {p1.stderr.read().decode() if p1.stderr else rc1}")

            pal_png = Path(tmpd) / "palette.png"
            subprocess.run(["ffmpeg", "-y", "-i", str(raw_mp4), "-vf", vf_pal, str(pal_png)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            subprocess.run(["ffmpeg", "-y", "-i", str(raw_mp4), "-i", str(pal_png), "-lavfi", f"[0:v][1:v]{vf_use}", "-loop", "0", str(gif_out)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--approval-dir", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=max(4, min(12, os.cpu_count() or 4)))
    args = ap.parse_args()

    repo = args.repo.resolve()
    appr = args.approval_dir.resolve()
    emblem_path = repo / "configs" / "icons" / "emblema-mestre-1254.png"
    emblem_surf = pil_to_cairo_surface(Image.open(emblem_path))

    wall_dir = repo / "configs" / "wallpapers"
    icon_dir = repo / "configs" / "icons"
    wall_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)

    d_limine = appr / "01-Limine"
    d_greeter = appr / "02-Noctalia-Greeter"
    d_lock = appr / "03-Noctalia-Lockscreen"
    d_g5 = appr / "04-Wallpapers-G5"
    d_aoc = appr / "05-Wallpapers-AOC"
    for d in (d_limine, d_greeter, d_lock, d_g5, d_aoc):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Static 4K masters + runtime PNGs
    print("Rendering 4K masters and static architectural backgrounds...")
    render_limine_bg(3840, 2160, emblem_surf).save(d_limine / "nox-limine-master-4k.png")
    lim_1080 = render_limine_bg(1920, 1080, emblem_surf)
    lim_1080.save(wall_dir / "nox-limine.png")
    shutil.copy2(wall_dir / "nox-limine.png", d_limine / "wallpaper-limine-1920x1080.png")

    render_greeter_bg(3840, 2160).save(d_greeter / "nox-greeter-master-4k.png")
    gr_1440 = render_greeter_bg(2560, 1440)
    gr_1440.save(wall_dir / "nox-greeter.png")
    shutil.copy2(wall_dir / "nox-greeter.png", d_greeter / "wallpaper-greeter.png")

    render_lockscreen_bg(3840, 2160, emblem_surf).save(d_lock / "nox-lockscreen-master-4k.png")
    lk_1440 = render_lockscreen_bg(2560, 1440, emblem_surf)
    lk_1440.save(wall_dir / "nox-lockscreen.png")
    shutil.copy2(wall_dir / "nox-lockscreen.png", d_lock / "wallpaper-lockscreen.png")

    # 2. G5 static 4K master + static 1440p fallback
    g5_p_4k = build_particles(46, 24, 80, 3760, 0, 2160, 2.0)
    g5_4k_rgb = render_g5_frame(3840, 2160, 0.0, emblem_surf, g5_p_4k)
    Image.frombytes("RGB", (3840, 2160), g5_4k_rgb).save(d_g5 / "nox-g5-master-4k.png")

    g5_p_1440 = build_particles(46, 24, 60, 2500, 0, 1440, 1.333)
    g5_1440_rgb = render_g5_frame(2560, 1440, 0.0, emblem_surf, g5_p_1440)
    Image.frombytes("RGB", (2560, 1440), g5_1440_rgb).save(wall_dir / "nox-g5.png")
    # Preserve default obsidian-purple.png alias aligned to G5 static artwork for backwards compat
    shutil.copy2(wall_dir / "nox-g5.png", wall_dir / "obsidian-purple.png")

    # 3. AOC static 4K portrait master + static 1080x1920 fallback
    aoc_p_4k = build_particles(56, 42, 60, 2100, 0, 3840, 2.0)
    aoc_4k_rgb = render_aoc_frame(2160, 3840, 0.0, emblem_surf, aoc_p_4k)
    Image.frombytes("RGB", (2160, 3840), aoc_4k_rgb).save(d_aoc / "nox-aoc-master-vertical-4k.png")

    aoc_p_1080 = build_particles(56, 42, 30, 1050, 0, 1920, 1.0)
    aoc_1080_rgb = render_aoc_frame(1080, 1920, 0.0, emblem_surf, aoc_p_1080)
    Image.frombytes("RGB", (1080, 1920), aoc_1080_rgb).save(wall_dir / "nox-aoc.png")

    # 4. Animated stickers & wallpapers
    print("Rendering Lockscreen transparent animated emblem GIF (360x360, 50fps, 6s loop)...")
    encode_video_and_gif("sticker", 360, 360, emblem_path, [], None, icon_dir / "nox-lockscreen-emblem.gif", args.workers)
    shutil.copy2(icon_dir / "nox-lockscreen-emblem.gif", d_lock / "nox-lockscreen-emblem.gif")

    print("Rendering G5 2560x1440 60fps WebM + 50fps GIF (6s loop)...")
    encode_video_and_gif("g5", 2560, 1440, emblem_path, g5_p_1440, wall_dir / "nox-g5-runtime.webm", d_g5 / "nox-g5-2560x1440.gif", args.workers)
    shutil.copy2(wall_dir / "nox-g5-runtime.webm", d_g5 / "nox-g5-runtime.webm")

    print("Rendering AOC 1080x1920 60fps WebM + 50fps GIF (6s loop)...")
    encode_video_and_gif("aoc", 1080, 1920, emblem_path, aoc_p_1080, wall_dir / "nox-aoc-runtime.webm", d_aoc / "nox-aoc-1080x1920.gif", args.workers)
    shutil.copy2(wall_dir / "nox-aoc-runtime.webm", d_aoc / "nox-aoc-runtime.webm")

    print("All Project Nox visual assets generated cleanly!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
