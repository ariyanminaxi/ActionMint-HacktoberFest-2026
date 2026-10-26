#!/usr/bin/env python3
"""Turn images on a flat key-color background into clean transparent PNGs.

Usage (from the project root):
  python scripts/keyout.py --all raw frontend/public/assets/categories      (every .png in a folder)
  python scripts/keyout.py raw/overview-a.png out/overview-a.png            (one file)
Options: --key FF00FF  --size 768  --pad 6  --shrink 1  --colors 256  --max-kb 400

Needs: pip install pillow numpy

What it does: estimates the background color from the image border (or uses --key), computes alpha from the
distance to that color, replaces edge colors with the nearby solid colors (no magenta halo), crops to the
subject, adds padding, resizes to --size (long edge) and saves an optimized PNG with real alpha.

Two-frame animations: files named <name>-a.png and <name>-b.png are treated as a pair. Both frames are cropped with
the SAME box and scaled by the SAME factor, so they line up exactly when the website flips between them.
"""
import argparse
import io
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

MAXD = 441.673  # sqrt(3) * 255
MAX_KB = 400  # size budget per output file


def border_key(rgb):
    edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(np.float32)
    return np.median(edge, axis=0)


def keyout(img, key=None, lo=0.07, hi=0.30):
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    k = border_key(rgb) if key is None else np.array(key, dtype=np.float32)
    d = np.linalg.norm(rgb - k, axis=2) / MAXD
    a = np.clip((d - lo) / (hi - lo), 0.0, 1.0)
    # Edge decontamination: edge pixels take their color from the nearby solid interior, so no key-color halo.
    solid_img = Image.fromarray((a >= 0.95).astype(np.uint8) * 255, "L").filter(ImageFilter.MinFilter(3))
    mask = np.asarray(solid_img, dtype=np.float32) / 255.0
    r = 3
    den = np.asarray(solid_img.filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255.0
    fg = rgb.copy()
    edge = (a < 0.95) & (a > 0.0) & (den > 0.02)
    for c in range(3):
        chan = Image.fromarray((rgb[..., c] * mask).round().astype(np.uint8), "L")
        num = np.asarray(chan.filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255.0
        est = np.clip(num / np.maximum(den, 1e-3) * 255.0, 0, 255)
        fg[..., c] = np.where(edge, est, fg[..., c])
    fg = np.where(a[..., None] > 0.0, fg, 0)
    out = np.dstack([fg, a * 255.0]).round().astype(np.uint8)
    return Image.fromarray(out, "RGBA"), k


def alpha_bbox(rgba):
    return rgba.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()


def finish_group(rgbas, size, pad, shrink):
    """Crop every image with the same (union) box and scale them by the same factor."""
    if shrink:
        for im in rgbas:
            a = im.getchannel("A")
            for _ in range(shrink):
                a = a.filter(ImageFilter.MinFilter(3))
            im.putalpha(a)
    boxes = [alpha_bbox(im) for im in rgbas]
    if any(b is None for b in boxes):
        raise ValueError("Nothing left after keying. Wrong key color, or the background is not flat.")
    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
    scale = min(1.0, size / max(w, h)) if size else 1.0
    tw, th = max(1, round(w * scale)), max(1, round(h * scale))
    outs = []
    for im in rgbas:
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        canvas.paste(im.crop((x0, y0, x1, y1)), (pad, pad))
        outs.append(canvas.resize((tw, th), Image.LANCZOS) if scale < 1.0 else canvas)
    return outs


def encode(img):
    buffer = io.BytesIO()
    img.save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


def palette_reduce(img, palette):
    return img.quantize(colors=palette, method=Image.Quantize.FASTOCTREE)


def group_encoder(outs, colors, max_kb):
    """Pick ONE encoding for every frame of a pair, so A and B match in colour depth.

    Encoding each frame independently would leave one RGBA and one palettised (as happened with
    flow-a/flow-b before this), and the A/B wiggle would visibly flicker between them.
    """
    budget = max_kb * 1024
    if colors:
        return (lambda img: palette_reduce(img, colors)), f"{colors}-color palette"
    if all(len(encode(img)) <= budget for img in outs):
        return (lambda img: img), "rgba"
    for palette in (256, 192, 128, 96, 64):
        if all(len(encode(palette_reduce(img, palette))) <= budget for img in outs):
            return (lambda img, p=palette: palette_reduce(img, p)), f"{palette}-color palette"
    return (lambda img: palette_reduce(img, 64)), "64-color palette (still over budget)"


def save(img, dst, used, max_kb=MAX_KB, key=None):
    """Write one prepared frame and report its size, encoding and any key-colour halo."""
    transparent = 100 * (np.asarray(img.convert("RGBA").getchannel("A")) == 0).mean()
    data = encode(img)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_bytes(data)
    kb = len(data) / 1024
    print(f"  {Path(dst).name}: {img.width}x{img.height}, {kb:.0f} KB, transparent {transparent:.0f}%, {used}")
    if kb > max_kb:
        print(f"    warning: still over {max_kb} KB; lower --size or --colors")
    if key is not None:
        rgba = np.asarray(Image.open(dst).convert("RGBA"), dtype=np.float32)
        alpha, rgb = rgba[..., 3], rgba[..., :3]
        keyed = (alpha > 8) & (np.linalg.norm(rgb - np.array(key, dtype=np.float32), axis=2) / MAXD < 0.14)
        share = 100 * keyed.mean()
        if share > 0.4:
            print(f"    warning: {share:.1f}% of pixels still look like the key colour (halo)")


def process_group(srcs, dsts, key, size, pad, shrink, colors, max_kb=MAX_KB):
    keyed = []
    detected = None
    for s in srcs:
        rgba, k = keyout(Image.open(s), key)
        keyed.append(rgba)
        detected = k
        print(f"{Path(s).name} (background {tuple(int(x) for x in k)})")
    outs = finish_group(keyed, size, pad, shrink)
    encoder, used = group_encoder(outs, colors, max_kb)
    for out, d in zip(outs, dsts):
        save(encoder(out), d, used, max_kb, detected)


def group_files(files):
    groups = {}
    for f in files:
        m = re.fullmatch(r"(.+)-([ab])", f.stem)
        groups.setdefault(m.group(1) if m else f.stem, []).append(f)
    return groups.values()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--all", action="store_true", help="src and dst are folders")
    p.add_argument("--key", help="hex key color, e.g. FF00FF (default: auto from the image border)")
    p.add_argument("--size", type=int, default=768, help="long edge in px (default 768)")
    p.add_argument("--pad", type=int, default=6)
    p.add_argument("--colors", type=int, default=0, help="palette size, e.g. 256, to make the PNG much smaller (0 = off)")
    p.add_argument("--shrink", type=int, default=0, help="erode the edge by N px if a thin light fringe remains")
    p.add_argument("--max-kb", type=int, default=MAX_KB, help=f"output size budget in KB (default {MAX_KB})")
    a = p.parse_args()
    key = tuple(int(a.key[i:i + 2], 16) for i in (0, 2, 4)) if a.key else None
    if a.all:
        files = sorted(Path(a.src).glob("*.png"))
        if not files:
            sys.exit("No .png files found in " + a.src)
        for grp in group_files(files):
            process_group(grp, [Path(a.dst) / f.name for f in grp], key, a.size, a.pad, a.shrink, a.colors, a.max_kb)
    else:
        process_group([a.src], [a.dst], key, a.size, a.pad, a.shrink, a.colors, a.max_kb)


if __name__ == "__main__":
    main()
