#!/usr/bin/env python3
"""Deterministic Project Nox Obsidian Purple visual asset generator.

Faithful to official Kit-Mestre & GitHub hero.svg references:
- Soft white / silver / faint-lilac cosmic snow particles (no gold/purple dots)
- Global tilted solar white-gold light sweep (sweepBeam / feixeLuminoso) crossing
  the ENTIRE frame cleanly from off-screen left to off-screen right, with a
  subtle synchronized metallic glint on gold emblem areas
- Zero unrequested horizontal/vertical lines, giant ovals, or sanctuary frames
- Unified visual language across Greeter, Lock Screen, Limine, G5, and AOC
"""
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
from PIL import Image, ImageFilter

_G_EMBLEM_SURF: cairo.ImageSurface | None = None
_G_GOLD_MASK_SURF: cairo.ImageSurface | None = None


def halton(index: int, base: int) -> float:
    result = 0.0
    f = 1.0 / base
    i = index
    while i > 0:
        result += f * (i % base)
        i //= base
        f /= base
    return result


def build_particles(
    count: int,
    seed_offset: int,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    scale: float,
) -> list[dict]:
    """Build official Kit-Mestre cosmic snow particles (soft white/silver/pale-lilac)."""
    items = []
    # Official Kit-Mestre snowWhite / snowSilver / snowLilac tones (zero yellow/violet dots)
    tones = [
        (1.00, 1.00, 1.00),  # snowWhite core
        (0.945, 0.961, 0.976),  # snowSilver (#f1f5f9)
        (0.961, 0.953, 1.000),  # snowLilac (#f5f3ff very pale)
    ]
    for idx in range(count):
        i = idx + 1 + seed_offset
        hx = halton(i + 3, 2)
        hy = halton(i + 5, 3)
        hd = halton(i + 7, 5)
        hs = halton(i + 11, 7)
        is_mid = (idx % 3 == 0)
        if is_mid:
            r = (4.0 + hd * 1.5) * scale
            max_op = 0.40 + hd * 0.16
            fall = (180 + hd * 80) * scale
        else:
            r = (2.5 + hd * 1.2) * scale
            max_op = 0.22 + hd * 0.16
            fall = (115 + hd * 60) * scale
        sway = (5.0 + hs * 9.0) * scale
        rgb = tones[idx % 3]
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
    a = arr[:, :, 3:4].astype(np.float32) / 255.0
    bgra = np.empty_like(arr)
    bgra[:, :, 0] = np.clip(arr[:, :, 2] * a[:, :, 0], 0, 255).astype(np.uint8)
    bgra[:, :, 1] = np.clip(arr[:, :, 1] * a[:, :, 0], 0, 255).astype(np.uint8)
    bgra[:, :, 2] = np.clip(arr[:, :, 0] * a[:, :, 0], 0, 255).astype(np.uint8)
    bgra[:, :, 3] = arr[:, :, 3]
    h, w = bgra.shape[:2]
    buf = bytearray(bgra.tobytes())
    return cairo.ImageSurface.create_for_data(buf, cairo.FORMAT_ARGB32, w, h, w * 4)


def build_gold_mask_image(emblem_img: Image.Image) -> Image.Image:
    """Extract a smooth alpha mask covering exclusively the warm gold metallic regions."""
    arr = np.array(emblem_img.convert("RGBA"), dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    # Gold pixels have strong warm R & G well above B; violet Lambda has high B relative to G/R
    warmth = np.clip((r - b - 18.0) / 55.0, 0.0, 1.0) * np.clip((g - b * 0.90) / 45.0, 0.0, 1.0)
    gold_alpha = np.clip((a / 255.0) * warmth * 255.0, 0, 255).astype(np.uint8)
    mask_img = Image.fromarray(gold_alpha, mode="L").filter(ImageFilter.GaussianBlur(radius=1.8))
    rgba_mask = Image.new("RGBA", emblem_img.size, (255, 255, 255, 0))
    rgba_mask.putalpha(mask_img)
    return rgba_mask


def draw_cosmic_background(
    ctx: cairo.Context, w: int, h: int, glow_cx: float, glow_cy: float, ambient_scale: float = 1.0
) -> None:
    bg = cairo.LinearGradient(0, 0, w, h)
    bg.add_color_stop_rgb(0.0, 0x09 / 255, 0x06 / 255, 0x10 / 255)
    bg.add_color_stop_rgb(0.48, 0x12 / 255, 0x0A / 255, 0x1F / 255)
    bg.add_color_stop_rgb(1.0, 0x08 / 255, 0x05 / 255, 0x0E / 255)
    ctx.set_source(bg)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    r_amb = max(w, h) * 0.60
    g1 = cairo.RadialGradient(w * 0.88, h * 0.28, 0, w * 0.88, h * 0.28, r_amb)
    g1.add_color_stop_rgba(0.0, 0x7C / 255, 0x3A / 255, 0xED / 255, 0.18 * ambient_scale)
    g1.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
    ctx.set_source(g1)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    g2 = cairo.RadialGradient(w * 0.50, h * 0.85, 0, w * 0.50, h * 0.85, max(w, h) * 0.55)
    g2.add_color_stop_rgba(0.0, 0x4C / 255, 0x1D / 255, 0x95 / 255, 0.12 * ambient_scale)
    g2.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
    ctx.set_source(g2)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    vig = cairo.RadialGradient(
        glow_cx, glow_cy, min(w, h) * 0.24, w * 0.5, h * 0.5, math.hypot(w, h) * 0.55
    )
    vig.add_color_stop_rgba(0.0, 0x05 / 255, 0x03 / 255, 0x0A / 255, 0.0)
    vig.add_color_stop_rgba(1.0, 0x05 / 255, 0x03 / 255, 0x0A / 255, 0.44)
    ctx.set_source(vig)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()


def draw_particles(ctx: cairo.Context, particles: list[dict], p: float, wrap_h: float) -> None:
    """Render soft unfocused distant cosmic snow particles (white / silver / faint lilac)."""
    for sp in particles:
        age = (p + sp["phase"]) % 1.0
        x = sp["x"] + sp["sway"] * math.sin(2 * math.pi * (p + sp["sway_phase"]))
        y = (sp["y"] + sp["fall"] * age) % wrap_h
        op = sp["max_op"] * math.sin(math.pi * age)
        if op <= 0.01:
            continue
        r, g, b = sp["rgb"]
        rad = sp["r"] * 2.2
        grad = cairo.RadialGradient(x, y, 0, x, y, rad)
        grad.add_color_stop_rgba(0.0, r, g, b, op * 0.88)
        grad.add_color_stop_rgba(0.36, r, g, b, op * 0.46)
        grad.add_color_stop_rgba(0.72, r, g, b, op * 0.12)
        grad.add_color_stop_rgba(1.0, r, g, b, 0.0)
        ctx.set_source(grad)
        ctx.arc(x, y, rad, 0, 2 * math.pi)
        ctx.fill()


def _compute_dual_sweep_global(
    p: float,
    p_start: float = 0.06,
    p_end: float = 0.78,
    bx_start: float = -660.0,
    bx_end: float = 4340.0,
    beam_w: float = 460.0,
) -> tuple[float, float, float, float] | None:
    """Single shared dual-monitor trajectory (G5 [0..2560, 0..1440] -> AOC [2560..3640, -350..1570]).

    Uses a C1 smooth trapezoidal velocity profile so speed remains uniform across the
    G5 -> AOC bezel boundary without stalling or restarting.
    """
    if p < p_start or p > p_end:
        return None
    u = (p - p_start) / (p_end - p_start)
    r = 0.12
    v_max = 1.0 / (1.0 - r)
    if u < r:
        pos = 0.5 * (u * u / r) * v_max
    elif u <= 1.0 - r:
        pos = (0.5 * r + (u - r)) * v_max
    else:
        rem = 1.0 - u
        pos = 1.0 - 0.5 * (rem * rem / r) * v_max

    # Smooth fade in/out only near the extreme off-screen boundaries; steady glow across both displays
    env = 1.0
    if u < 0.08:
        env = math.sin((u / 0.08) * (math.pi * 0.5))
    elif u > 0.92:
        env = math.sin(((1.0 - u) / 0.08) * (math.pi * 0.5))

    tilt_tan = math.tan(math.radians(-20.0))
    bx_global = bx_start + (bx_end - bx_start) * pos
    return bx_global, tilt_tan, beam_w, env


def draw_dual_global_light_sweep(
    ctx: cairo.Context,
    out_x: float,
    out_y: float,
    w: int,
    h: int,
    p: float,
    peak_center_alpha: float = 0.165,
) -> tuple[float, float, float, float] | None:
    """Render the shared global light sweep projected onto monitor rectangle (out_x, out_y, w, h)."""
    state = _compute_dual_sweep_global(p)
    if state is None:
        return None
    bx_global, tilt_tan, beam_w, env = state
    peak_op = peak_center_alpha * env
    if peak_op <= 0.002:
        return None

    # Local X at y_local = 0 (y_virtual = out_y)
    bx_local = bx_global + (out_y * tilt_tan) - out_x
    # Early skip if beam is completely outside this output's horizontal span
    min_x = bx_local + min(0.0, h * tilt_tan)
    max_x = bx_local + beam_w + max(0.0, h * tilt_tan)
    if max_x < -40.0 or min_x > w + 40.0:
        return bx_local, tilt_tan, beam_w, env

    ctx.save()
    ctx.transform(cairo.Matrix(1.0, 0.0, tilt_tan, 1.0, bx_local, 0.0))
    grad = cairo.LinearGradient(0.0, 0.0, beam_w, 0.0)
    grad.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.0)
    grad.add_color_stop_rgba(0.18, 0xFE / 255, 0xF0 / 255, 0x8A / 255, peak_op * 0.12)
    grad.add_color_stop_rgba(0.35, 0xFE / 255, 0xF0 / 255, 0x8A / 255, peak_op * 0.44)
    grad.add_color_stop_rgba(0.50, 0xFE / 255, 0xF0 / 255, 0x8A / 255, peak_op)
    grad.add_color_stop_rgba(0.65, 0xFE / 255, 0xF0 / 255, 0x8A / 255, peak_op * 0.44)
    grad.add_color_stop_rgba(0.82, 0xFE / 255, 0xF0 / 255, 0x8A / 255, peak_op * 0.12)
    grad.add_color_stop_rgba(1.00, 1.0, 1.0, 1.0, 0.0)
    ctx.set_operator(cairo.OPERATOR_SCREEN)
    ctx.set_source(grad)
    ctx.rectangle(0.0, -h * 0.12, beam_w, h * 1.24)
    ctx.fill()
    ctx.restore()
    return bx_local, tilt_tan, beam_w, env


def draw_gold_light_sweep_at(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    emblem_diam: float,
    gold_mask_surf: cairo.ImageSurface | None,
    bx_canvas: float,
    tilt_tan: float,
    beam_w_canvas: float,
    env: float,
    peak_gold_op: float = 0.24,
) -> None:
    """Optional secondary metallic glint clipped to gold metal in exact sync with the global sweep."""
    if gold_mask_surf is None or env <= 0.01:
        return
    src_w = float(gold_mask_surf.get_width())
    src_h = float(gold_mask_surf.get_height())
    scale_e = emblem_diam / src_w
    em_x0 = cx - emblem_diam / 2.0
    em_y0 = cy - emblem_diam / 2.0

    # Convert global canvas beam coordinates into local emblem surface coordinates
    local_bx = ((bx_canvas + em_y0 * tilt_tan) - em_x0) / scale_e
    local_bw = beam_w_canvas / scale_e
    if local_bx + local_bw < -src_w * 0.6 or local_bx - src_h * abs(tilt_tan) > src_w * 1.6:
        return

    peak_op = peak_gold_op * env
    sweep_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(src_w), int(src_h))
    sctx = cairo.Context(sweep_surf)
    sctx.save()
    sctx.transform(cairo.Matrix(1.0, 0.0, tilt_tan, 1.0, local_bx, 0.0))
    grad = cairo.LinearGradient(0.0, 0.0, local_bw, 0.0)
    grad.add_color_stop_rgba(0.00, 1.0, 1.0, 1.0, 0.0)
    grad.add_color_stop_rgba(0.25, 1.0, 0.96, 0.72, peak_op * 0.22)
    grad.add_color_stop_rgba(0.50, 1.0, 0.99, 0.92, peak_op)
    grad.add_color_stop_rgba(0.75, 1.0, 0.96, 0.72, peak_op * 0.22)
    grad.add_color_stop_rgba(1.00, 1.0, 1.0, 1.0, 0.0)
    sctx.set_source(grad)
    sctx.rectangle(0.0, -src_h * 0.25, local_bw, src_h * 1.5)
    sctx.fill()
    sctx.restore()

    sctx.set_operator(cairo.OPERATOR_DEST_IN)
    sctx.set_source_surface(gold_mask_surf, 0.0, 0.0)
    sctx.paint()

    ctx.save()
    ctx.translate(em_x0, em_y0)
    ctx.scale(scale_e, scale_e)
    pat = cairo.SurfacePattern(sweep_surf)
    pat.set_filter(cairo.FILTER_BEST)
    ctx.set_operator(cairo.OPERATOR_SCREEN)
    ctx.set_source(pat)
    ctx.paint()
    ctx.restore()


def draw_gold_light_sweep(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    emblem_diam: float,
    p: float,
    gold_mask_surf: cairo.ImageSurface | None,
) -> None:
    """Self-contained sweep helper for isolated sticker/emblem renders."""
    if gold_mask_surf is None:
        return
    p_start, p_end = 0.08, 0.56
    if p < p_start or p > p_end:
        return
    u = (p - p_start) / (p_end - p_start)
    eased = u * u * (3.0 - 2.0 * u)
    env = math.sin(math.pi * u) ** 1.25
    bx_local = cx - emblem_diam * 0.75 + (emblem_diam * 1.65) * eased
    tilt_tan = math.tan(math.radians(-20.0))
    draw_gold_light_sweep_at(
        ctx, cx, cy, emblem_diam, gold_mask_surf, bx_local, tilt_tan, emblem_diam * 0.36, env, 0.38
    )


def draw_emblem_orbital_assembly(
    ctx: cairo.Context,
    cx: float,
    cy: float,
    emblem_diam: float,
    p: float,
    emblem_surf: cairo.ImageSurface,
    gold_mask_surf: cairo.ImageSurface | None = None,
    draw_glows: bool = True,
    local_gold_sweep: bool = True,
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
        neb.add_color_stop_rgba(0.0, 0x93 / 255, 0x33 / 255, 0xEA / 255, 0.46 * aurora_op)
        neb.add_color_stop_rgba(0.52, 0x58 / 255, 0x1C / 255, 0x87 / 255, 0.20 * aurora_op)
        neb.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
        ctx.set_source(neb)
        ctx.arc(0, 0, neb_r, 0, 2 * math.pi)
        ctx.fill()

        gold_r = emblem_diam * 0.58
        gcore = cairo.RadialGradient(0, 0, 0, 0, 0, gold_r)
        gcore.add_color_stop_rgba(0.0, 0xFB / 255, 0xBF / 255, 0x24 / 255, 0.26 * aurora_op)
        gcore.add_color_stop_rgba(0.60, 0xD9 / 255, 0x77 / 255, 0x06 / 255, 0.08 * aurora_op)
        gcore.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
        ctx.set_source(gcore)
        ctx.arc(0, 0, gold_r, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

    # Outer dashed orbit (+180 deg)
    unit_outer = (2 * math.pi * r_outer) / 360.0
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(math.radians(180.0 * p))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_dash([15 * unit_outer, 6 * unit_outer, 4 * unit_outer, 5 * unit_outer])
    ctx.set_line_width(emblem_diam * 0.017)
    ctx.set_source_rgba(0xA8 / 255, 0x55 / 255, 0xF7 / 255, 0.22)
    ctx.arc(0, 0, r_outer, 0, 2 * math.pi)
    ctx.stroke()
    og = cairo.LinearGradient(-r_outer, -r_outer, r_outer, r_outer)
    og.add_color_stop_rgba(0.0, 0xFB / 255, 0xBF / 255, 0x24 / 255, 0.94)
    og.add_color_stop_rgba(0.5, 0xA8 / 255, 0x55 / 255, 0xF7 / 255, 0.45)
    og.add_color_stop_rgba(1.0, 0xF5 / 255, 0x9E / 255, 0x0B / 255, 0.94)
    ctx.set_source(og)
    ctx.set_line_width(emblem_diam * 0.0118)
    ctx.arc(0, 0, r_outer, 0, 2 * math.pi)
    ctx.stroke()
    ctx.restore()

    # Inner dashed orbit (-420 deg)
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
    ctx.set_line_width(emblem_diam * 0.009)
    ctx.set_source_rgba(0xB9 / 255, 0x73 / 255, 0xFA / 255, 0.80)
    ctx.arc(0, 0, r_inner, 0, 2 * math.pi)
    ctx.stroke()
    ctx.restore()

    # Official emblem raster
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

    # Optional local solar metallic sheen (used by isolated sticker GIF)
    if local_gold_sweep:
        draw_gold_light_sweep(ctx, cx, cy, emblem_diam, p, gold_mask_surf)

    # Outer golden satellite (+360 deg)
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

    # Inner magenta satellite (-360 deg)
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
    """Kept exclusively for Limine approved framing."""
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
        ctx.set_source_rgba(0xFB / 255, 0xBF / 255, 0x24 / 255, 0.85)
        ctx.arc(x0, y0, lw * 1.4, 0, 2 * math.pi)
        ctx.fill()
    ctx.restore()


def draw_thin_divider(ctx: cairo.Context, cx: float, y: float, width: float, thickness: float) -> None:
    x0 = cx - width / 2
    g = cairo.LinearGradient(x0, y, x0 + width, y)
    g.add_color_stop_rgba(0.0, 0x6B / 255, 0x21 / 255, 0xA8 / 255, 0.0)
    g.add_color_stop_rgba(0.25, 0x7C / 255, 0x3A / 255, 0xED / 255, 0.45)
    g.add_color_stop_rgba(0.50, 0xD9 / 255, 0x77 / 255, 0x06 / 255, 0.85)
    g.add_color_stop_rgba(0.75, 0x7C / 255, 0x3A / 255, 0xED / 255, 0.45)
    g.add_color_stop_rgba(1.0, 0x6B / 255, 0x21 / 255, 0xA8 / 255, 0.0)
    ctx.set_source(g)
    ctx.set_line_width(thickness)
    ctx.move_to(x0, y)
    ctx.line_to(x0 + width, y)
    ctx.stroke()
    ctx.set_source_rgba(0xFB / 255, 0xBF / 255, 0x24 / 255, 0.90)
    ctx.arc(cx, y, thickness * 1.8, 0, 2 * math.pi)
    ctx.fill()


def render_g5_frame(
    w: int,
    h: int,
    p: float,
    emblem_surf: cairo.ImageSurface,
    gold_mask_surf: cairo.ImageSurface | None,
    particles: list[dict],
) -> bytes:
    """Horizontal G5 (left, [0, 0]) fed by unified 14s dual-monitor light-sweep trajectory."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    cx, cy = w * 0.50, h * 0.50
    diam = h * 0.36
    draw_cosmic_background(ctx, w, h, cx, cy, 1.0)
    draw_particles(ctx, particles, p, float(h))
    draw_emblem_orbital_assembly(
        ctx, cx, cy, diam, p, emblem_surf, gold_mask_surf, draw_glows=True, local_gold_sweep=False
    )
    scale_x = w / 2560.0
    sweep_info = draw_dual_global_light_sweep(ctx, 0.0, 0.0, w, h, p, peak_center_alpha=0.165)
    if sweep_info is not None and scale_x == 1.0:
        bx_local, tilt_tan, beam_w, env = sweep_info
        draw_gold_light_sweep_at(ctx, cx, cy, diam, gold_mask_surf, bx_local, tilt_tan, beam_w, env, 0.18)
    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return rgb.tobytes()


def render_aoc_frame(
    w: int,
    h: int,
    p: float,
    emblem_surf: cairo.ImageSurface,
    gold_mask_surf: cairo.ImageSurface | None,
    particles: list[dict],
    aoc_x: float = 2560.0,
    aoc_y: float = -350.0,
) -> bytes:
    """Portrait AOC (right, [2560, -350]) continuing the identical 14s dual-monitor light-sweep trajectory."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    cx, cy = w * 0.50, h * 0.45
    diam = w * 0.44
    draw_cosmic_background(ctx, w, h, cx, cy, 1.0)
    draw_particles(ctx, particles, p, float(h))
    draw_emblem_orbital_assembly(
        ctx, cx, cy, diam, p, emblem_surf, gold_mask_surf, draw_glows=True, local_gold_sweep=False
    )
    scale_x = w / 1080.0
    sweep_info = draw_dual_global_light_sweep(ctx, aoc_x, aoc_y, w, h, p, peak_center_alpha=0.165)
    if sweep_info is not None and scale_x == 1.0:
        bx_local, tilt_tan, beam_w, env = sweep_info
        draw_gold_light_sweep_at(ctx, cx, cy, diam, gold_mask_surf, bx_local, tilt_tan, beam_w, env, 0.18)
    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return rgb.tobytes()


def render_sticker_frame(
    size: int,
    p: float,
    emblem_surf: cairo.ImageSurface,
    gold_mask_surf: cairo.ImageSurface | None,
) -> bytes:
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surf)
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)
    draw_emblem_orbital_assembly(
        ctx, size * 0.5, size * 0.5, size * 0.72, p, emblem_surf, gold_mask_surf, draw_glows=True, local_gold_sweep=True
    )
    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((size, size, 4)).copy()
    rgba = arr[:, :, [2, 1, 0, 3]].astype(np.float32)
    a = rgba[:, :, 3:4]
    nz = a[:, :, 0] > 0
    for c in range(3):
        rgba[nz, c] = np.clip((rgba[nz, c] * 255.0) / a[nz, 0], 0, 255)
    return rgba.astype(np.uint8).tobytes()


def _draw_auth_stage_atmosphere(ctx: cairo.Context, w: int, h: int, emblem_cy: float) -> None:
    """Shared cosmic nebula depth behind the Greeter & Lock Screen crest + authentication card."""
    draw_cosmic_background(ctx, w, h, w * 0.50, emblem_cy, 0.92)
    # Soft central atmospheric violet bloom behind the login/unlock card (no hard shapes)
    card_glow = cairo.RadialGradient(w * 0.50, h * 0.55, 0, w * 0.50, h * 0.55, h * 0.48)
    card_glow.add_color_stop_rgba(0.0, 0x6D / 255, 0x28 / 255, 0xD9 / 255, 0.14)
    card_glow.add_color_stop_rgba(0.55, 0x4C / 255, 0x1D / 255, 0x95 / 255, 0.05)
    card_glow.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
    ctx.set_source(card_glow)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()
    parts = build_particles(42, 24, w * 0.04, w * 0.96, h * 0.03, h * 0.96, h / 1080.0)
    draw_particles(ctx, parts, 0.20, float(h))


def render_lockscreen_bg(w: int, h: int) -> Image.Image:
    """Clean dark cosmic background unified identically with Greeter (no extra lines/frames)."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    emblem_cy = h * 0.135
    _draw_auth_stage_atmosphere(ctx, w, h, emblem_cy)

    # Subtle focal aura behind the animated lockscreen sticker zone
    neb = cairo.RadialGradient(w * 0.50, emblem_cy, 0, w * 0.50, emblem_cy, h * 0.24)
    neb.add_color_stop_rgba(0.0, 0x93 / 255, 0x33 / 255, 0xEA / 255, 0.30)
    neb.add_color_stop_rgba(0.55, 0x58 / 255, 0x1C / 255, 0x87 / 255, 0.10)
    neb.add_color_stop_rgba(1.0, 0x09 / 255, 0x06 / 255, 0x10 / 255, 0.0)
    ctx.set_source(neb)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()

    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return Image.fromarray(rgb, mode="RGB")


def render_greeter_bg(
    w: int,
    h: int,
    emblem_surf: cairo.ImageSurface,
    gold_mask_surf: cairo.ImageSurface | None,
) -> Image.Image:
    """Unified Greeter composition matching Lock Screen: official orbital emblem at top, clean cosmic snow, NO giant oval."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    emblem_cy = h * 0.120
    _draw_auth_stage_atmosphere(ctx, w, h, emblem_cy)

    # Official emblem prominent in upper-center crest above clock & login card
    draw_emblem_orbital_assembly(
        ctx, w * 0.50, emblem_cy, h * 0.132, 0.22, emblem_surf, gold_mask_surf, draw_glows=True, local_gold_sweep=False
    )

    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return Image.fromarray(rgb, mode="RGB")


def render_limine_bg(
    w: int,
    h: int,
    emblem_surf: cairo.ImageSurface,
    gold_mask_surf: cairo.ImageSurface | None,
) -> Image.Image:
    """Preserve approved Limine menu layout & top-right emblem while fixing background particles to cosmic snow."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(surf)
    draw_cosmic_background(ctx, w, h, w * 0.87, h * 0.18, 0.55)
    parts = build_particles(28, 202, w * 0.04, w * 0.96, h * 0.04, h * 0.96, h / 1080.0)
    draw_particles(ctx, parts, 0.18, float(h))

    draw_corner_brackets(ctx, w, h, h * 0.04, h * 0.042, max(1.5, h * 0.0018))
    draw_emblem_orbital_assembly(
        ctx, w * 0.875, h * 0.20, h * 0.175, 0.24, emblem_surf, gold_mask_surf, draw_glows=True
    )
    draw_thin_divider(ctx, w * 0.50, h * 0.915, w * 0.52, max(1.2, h * 0.0013))

    arr = np.frombuffer(surf.get_data(), dtype=np.uint8).reshape((h, w, 4))
    rgb = arr[:, :, [2, 1, 0]].copy()
    return Image.fromarray(rgb, mode="RGB")


def _worker_frame(task: tuple) -> tuple[int, bytes]:
    kind, idx, total, w, h, emblem_path, particles, aoc_x, aoc_y = task
    global _G_EMBLEM_SURF, _G_GOLD_MASK_SURF
    if _G_EMBLEM_SURF is None:
        em_img = Image.open(emblem_path)
        _G_EMBLEM_SURF = pil_to_cairo_surface(em_img)
        _G_GOLD_MASK_SURF = pil_to_cairo_surface(build_gold_mask_image(em_img))
    p = idx / total
    if kind == "g5":
        return idx, render_g5_frame(w, h, p, _G_EMBLEM_SURF, _G_GOLD_MASK_SURF, particles)
    if kind == "aoc":
        return idx, render_aoc_frame(w, h, p, _G_EMBLEM_SURF, _G_GOLD_MASK_SURF, particles, aoc_x=aoc_x, aoc_y=aoc_y)
    return idx, render_sticker_frame(w, p, _G_EMBLEM_SURF, _G_GOLD_MASK_SURF)


def encode_video_and_gif(
    kind: str,
    w: int,
    h: int,
    emblem_path: Path,
    particles: list[dict],
    webm_out: Path | None,
    gif_out: Path | None,
    workers: int,
    aoc_x: float = 2560.0,
    aoc_y: float = -350.0,
) -> None:
    if webm_out is not None:
        # 14.0s unified dual-monitor sweep loop (840 frames @ 60fps) for wallpapers; 6.0s for sticker
        fps_w, n_w = (60, 840) if kind in ("g5", "aoc") else (60, 360)
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
        tasks = [(kind, i, n_w, w, h, str(emblem_path), particles, aoc_x, aoc_y) for i in range(n_w)]
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for _idx, raw in ex.map(_worker_frame, tasks, chunksize=8):
                proc.stdin.write(raw)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg webm failed: {proc.stderr.read().decode() if proc.stderr else rc}")

    if gif_out is not None:
        # Match exact 14.0s unified dual-monitor cycle @ 20fps (280 frames) and 6.0s @ 50fps for sticker
        fps_g, n_g = (20, 280) if kind in ("g5", "aoc") else (50, 300)
        gif_out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpd:
            raw_nut = Path(tmpd) / "lossless.nut"
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
                "-c:v", "rawvideo", "-pix_fmt", pix_in, str(raw_nut),
            ]
            p1 = subprocess.Popen(cmd_cap, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            assert p1.stdin is not None
            tasks = [(kind, i, n_g, w, h, str(emblem_path), particles, aoc_x, aoc_y) for i in range(n_g)]
            with ProcessPoolExecutor(max_workers=workers) as ex:
                for _idx, raw in ex.map(_worker_frame, tasks, chunksize=8):
                    p1.stdin.write(raw)
            p1.stdin.close()
            rc1 = p1.wait()
            if rc1 != 0:
                raise RuntimeError(f"ffmpeg capture failed: {p1.stderr.read().decode() if p1.stderr else rc1}")

            pal_png = Path(tmpd) / "palette.png"
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(raw_nut), "-vf", vf_pal, str(pal_png)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(raw_nut), "-i", str(pal_png), "-lavfi", f"[0:v][1:v]{vf_use}", "-loop", "0", str(gif_out)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--approval-dir", type=Path, required=True)
    ap.add_argument("--skip-limine", action="store_true", help="Preserve existing approved nox-limine.png untouched")
    ap.add_argument("--aoc-x", type=float, default=2560.0, help="AOC virtual X origin (G5 right edge = 2560)")
    ap.add_argument("--aoc-y", type=float, default=-350.0, help="AOC virtual Y origin from hardware profile")
    ap.add_argument("--workers", type=int, default=max(4, min(12, os.cpu_count() or 4)))
    args = ap.parse_args()

    repo = args.repo.resolve()
    appr = args.approval_dir.resolve()
    emblem_path = repo / "configs" / "icons" / "emblema-mestre-1254.png"
    em_img = Image.open(emblem_path)
    emblem_surf = pil_to_cairo_surface(em_img)
    gold_mask_surf = pil_to_cairo_surface(build_gold_mask_image(em_img))

    wall_dir = repo / "configs" / "wallpapers"
    icon_dir = repo / "configs" / "icons"
    wall_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)

    is_dual = appr.name == "REFINAMENTO-DUAL-MONITOR"
    is_ref = appr.name == "REFINAMENTO-FINAL"
    d_limine = appr / "06-Limine"
    if is_dual:
        d_g5 = appr / "02-G5"
        d_g5_webm = d_g5 / "WebM-final"
        d_g5_gif = d_g5 / "GIF-final"
        d_aoc = appr / "03-AOC"
        d_aoc_webm = d_aoc / "WebM-final"
        d_aoc_gif = d_aoc / "GIF-final"
        d_greeter = appr / "05-Greeter"
        d_lock = appr / "06-LockScreen"
        for d in (
            appr / "01-Referencias", d_g5_webm, d_g5_gif, d_g5 / "Frames",
            d_aoc_webm, d_aoc_gif, d_aoc / "Frames",
            appr / "04-Animacao-Conjunta" / "timeline",
            appr / "04-Animacao-Conjunta" / "comparacoes",
            d_greeter, d_lock, appr / "07-Avatar", appr / "08-Relatorio",
        ):
            d.mkdir(parents=True, exist_ok=True)
    else:
        d_greeter = appr / ("04-Greeter" if is_ref else "02-Greeter")
        d_lock = appr / ("05-LockScreen" if is_ref else "03-LockScreen")
        d_g5 = appr / ("02-Feixe-Global-G5" if is_ref else "04-G5")
        d_aoc = appr / ("03-Feixe-Global-AOC" if is_ref else "05-AOC")
        d_g5_webm = d_g5
        d_g5_gif = d_g5
        d_aoc_webm = d_aoc
        d_aoc_gif = d_aoc
        for d in (d_greeter, d_lock, d_g5, d_aoc):
            d.mkdir(parents=True, exist_ok=True)

    print("Rendering 4K masters and unified static backgrounds...")
    if not args.skip_limine:
        d_limine.mkdir(parents=True, exist_ok=True)
        render_limine_bg(3840, 2160, emblem_surf, gold_mask_surf).save(d_limine / "nox-limine-master-4k.png")
        lim_1080 = render_limine_bg(1920, 1080, emblem_surf, gold_mask_surf)
        lim_1080.save(wall_dir / "nox-limine.png")
        shutil.copy2(wall_dir / "nox-limine.png", d_limine / "nox-limine.png")

    render_greeter_bg(3840, 2160, emblem_surf, gold_mask_surf).save(d_greeter / "nox-greeter-master-4k.png")
    gr_1440 = render_greeter_bg(2560, 1440, emblem_surf, gold_mask_surf)
    gr_1440.save(wall_dir / "nox-greeter.png")
    shutil.copy2(wall_dir / "nox-greeter.png", d_greeter / "nox-greeter.png")

    render_lockscreen_bg(3840, 2160).save(d_lock / "nox-lockscreen-master-4k.png")
    lk_1440 = render_lockscreen_bg(2560, 1440)
    lk_1440.save(wall_dir / "nox-lockscreen.png")
    shutil.copy2(wall_dir / "nox-lockscreen.png", d_lock / "nox-lockscreen.png")

    # G5 horizontal (static 4K master + 2560x1440 at calm phase p=0.03, zero permanent stripe)
    g5_p_4k = build_particles(42, 24, 80, 3760, 0, 2160, 2.0)
    g5_4k_rgb = render_g5_frame(3840, 2160, 0.03, emblem_surf, gold_mask_surf, g5_p_4k)
    Image.frombytes("RGB", (3840, 2160), g5_4k_rgb).save(d_g5 / "nox-g5-master-4k.png")

    g5_p_1440 = build_particles(42, 24, 60, 2500, 0, 1440, 1.333)
    g5_1440_rgb = render_g5_frame(2560, 1440, 0.03, emblem_surf, gold_mask_surf, g5_p_1440)
    Image.frombytes("RGB", (2560, 1440), g5_1440_rgb).save(wall_dir / "nox-g5.png")
    shutil.copy2(wall_dir / "nox-g5.png", d_g5 / "nox-g5.png")
    shutil.copy2(wall_dir / "nox-g5.png", wall_dir / "obsidian-purple.png")

    # AOC vertical (static 4K portrait master + 1080x1920 at calm phase p=0.03, zero permanent stripe)
    aoc_p_4k = build_particles(46, 42, 60, 2100, 0, 3840, 2.0)
    aoc_4k_rgb = render_aoc_frame(
        2160, 3840, 0.03, emblem_surf, gold_mask_surf, aoc_p_4k, aoc_x=args.aoc_x, aoc_y=args.aoc_y
    )
    Image.frombytes("RGB", (2160, 3840), aoc_4k_rgb).save(d_aoc / "nox-aoc-master-vertical-4k.png")

    aoc_p_1080 = build_particles(46, 42, 30, 1050, 0, 1920, 1.0)
    aoc_1080_rgb = render_aoc_frame(
        1080, 1920, 0.03, emblem_surf, gold_mask_surf, aoc_p_1080, aoc_x=args.aoc_x, aoc_y=args.aoc_y
    )
    Image.frombytes("RGB", (1080, 1920), aoc_1080_rgb).save(wall_dir / "nox-aoc.png")
    shutil.copy2(wall_dir / "nox-aoc.png", d_aoc / "nox-aoc.png")

    print("Rendering Lockscreen transparent animated emblem GIF (360x360, 50fps, 6s loop)...")
    encode_video_and_gif("sticker", 360, 360, emblem_path, [], None, icon_dir / "nox-lockscreen-emblem.gif", args.workers)
    shutil.copy2(icon_dir / "nox-lockscreen-emblem.gif", d_lock / "nox-lockscreen-emblem.gif")

    print("Rendering G5 2560x1440 60fps WebM + 20fps GIF (14s dual-monitor global-sweep loop)...")
    encode_video_and_gif(
        "g5", 2560, 1440, emblem_path, g5_p_1440,
        wall_dir / "nox-g5-runtime.webm", d_g5_gif / "nox-g5-2560x1440.gif", args.workers,
    )
    shutil.copy2(wall_dir / "nox-g5-runtime.webm", d_g5_webm / "nox-g5-runtime.webm")

    print("Rendering AOC 1080x1920 60fps WebM + 20fps GIF (14s dual-monitor global-sweep loop)...")
    encode_video_and_gif(
        "aoc", 1080, 1920, emblem_path, aoc_p_1080,
        wall_dir / "nox-aoc-runtime.webm", d_aoc_gif / "nox-aoc-1080x1920.gif", args.workers,
        aoc_x=args.aoc_x, aoc_y=args.aoc_y,
    )
    shutil.copy2(wall_dir / "nox-aoc-runtime.webm", d_aoc_webm / "nox-aoc-runtime.webm")

    print("All Project Nox visual assets regenerated cleanly!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
