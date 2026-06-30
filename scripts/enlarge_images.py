#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reprocesa las fotos de producto para que el artículo LLENE la tarjeta:
recorta el margen blanco sobrante y lo deja en un lienzo cuadrado con un
margen mínimo. Así el producto se ve grande sin perder nitidez (usa los
píxeles nativos, no hace upscale agresivo).

Trabaja sobre public/assets/products/ in-place.

Uso:  python scripts/enlarge_images.py
"""
import os, glob
from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIR = os.path.join(ROOT, "public", "assets", "products")

MARGIN = 0.06        # margen alrededor del producto (6%)
WHITE_THRESHOLD = 12 # cuánto se aleja del blanco puro para contar como contenido
MIN_SIDE = 480       # lado mínimo del lienzo final (para pantallas nítidas)


def trim_white(im):
    """Recorta el borde blanco; devuelve la imagen recortada al contenido."""
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L")
    mask = diff.point(lambda p: 255 if p > WHITE_THRESHOLD else 0)
    bbox = mask.getbbox()
    if not bbox:
        return im  # todo blanco: dejar como está
    return im.crop(bbox)


def process(path):
    im = Image.open(path).convert("RGB")
    content = trim_white(im)
    w, h = content.size
    side = max(w, h)
    canvas_side = int(round(side * (1 + 2 * MARGIN)))
    # escalar levemente si quedó muy chico, para nitidez en pantallas grandes
    if canvas_side < MIN_SIDE:
        scale = MIN_SIDE / canvas_side
        content = content.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        w, h = content.size
        side = max(w, h)
        canvas_side = MIN_SIDE
    canvas = Image.new("RGB", (canvas_side, canvas_side), (255, 255, 255))
    canvas.paste(content, ((canvas_side - w) // 2, (canvas_side - h) // 2))
    canvas.save(path, "JPEG", quality=90)
    return im.size, (canvas_side, canvas_side)


def main():
    files = sorted(glob.glob(os.path.join(DIR, "*.jpg")))
    if not files:
        raise SystemExit("No hay imágenes en " + DIR)
    before = after = 0
    for f in files:
        b, a = process(f)
        before += b[0]; after += a[0]
    print(f"OK: reprocesadas {len(files)} imágenes.")
    print(f"   lado promedio antes ~{before//len(files)}px -> lienzo después ~{after//len(files)}px "
          f"(el producto ahora llena el marco).")


if __name__ == "__main__":
    main()
