#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Genera el PDF del catalogo Albadur a partir de assets/data/products.json y
las fotos en assets/products/.

Salida: Catalogo-Albadur.pdf (en la raiz del repo)

Uso:  python scripts/build_pdf.py
"""
import json
import os
import textwrap

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "assets", "data", "products.json")
OUT = os.path.join(ROOT, "Catalogo-Albadur.pdf")
LOGO = os.path.join(ROOT, "assets", "img", "logo-square.jpg")
LOGO_WIDE = os.path.join(ROOT, "assets", "img", "logo.jpg")

W, H = A4
EMAIL = "sociedadalbadur@gmail.com"
YEAR = "2026"

COLORS = {
    "Confites":         (0.60, 0.30, 0.61),
    "Higiene Personal": (0.00, 0.46, 0.75),
    "Refrescos":        (0.00, 0.65, 0.56),
    "Despensa":         (0.98, 0.65, 0.20),
    "Menaje":           (0.27, 0.33, 0.38),
    "Libreria":         (0.89, 0.10, 0.13),
}
LABEL = {"Libreria": "Libreria"}  # reportlab base font sin tilde; ver nota abajo

MARGIN = 14 * mm
COLS = 3
GAP = 7 * mm
BAND_H = 12 * mm
NAME_H = 13 * mm
ROW_GAP = 6 * mm


def label(cat):
    return {"Libreria": "Librería"}.get(cat, cat)


def draw_cover(c):
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # franja superior de colores de marca
    band = H - 8 * mm
    seg = W / 6
    for i, col in enumerate([
        (0.00, 0.46, 0.75), (0.00, 0.65, 0.56), (0.89, 0.10, 0.13),
        (0.98, 0.65, 0.20), (0.60, 0.30, 0.61), (0.27, 0.33, 0.38)]):
        c.setFillColorRGB(*col)
        c.rect(i * seg, band, seg, 8 * mm, fill=1, stroke=0)

    # logo
    try:
        img = ImageReader(LOGO)
        size = 70 * mm
        c.drawImage(img, (W - size) / 2, H * 0.50, size, size,
                    preserveAspectRatio=True, mask='auto')
    except Exception:
        pass

    c.setFillColorRGB(0.12, 0.16, 0.19)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(W / 2, H * 0.42, "Catálogo de productos")

    c.setFont("Helvetica", 14)
    c.setFillColorRGB(0.42, 0.48, 0.52)
    c.drawCentredString(W / 2, H * 0.42 - 22, "Sociedad Albadur · Venta al por mayor")

    c.setFont("Helvetica", 12)
    c.drawCentredString(W / 2, 30 * mm, EMAIL)
    c.setFillColorRGB(0.6, 0.66, 0.7)
    c.setFont("Helvetica", 10)
    c.drawCentredString(W / 2, 22 * mm, "Edición " + YEAR)
    c.showPage()


def draw_band(c, cat, cont=False):
    col = COLORS.get(cat, (0.27, 0.33, 0.38))
    y = H - MARGIN - BAND_H
    c.setFillColorRGB(*col)
    c.roundRect(MARGIN, y, W - 2 * MARGIN, BAND_H, 4, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 15)
    txt = label(cat).upper() + ("  (continuación)" if cont else "")
    c.drawString(MARGIN + 6 * mm, y + BAND_H / 2 - 5, txt)
    return y


def wrap_name(c, name, max_w, font="Helvetica", size=8):
    c.setFont(font, size)
    words = name.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if c.stringWidth(test, font, size) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


def draw_footer(c, page_no):
    c.setFillColorRGB(0.6, 0.66, 0.7)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W / 2, 8 * mm, f"Sociedad Albadur · {EMAIL} · pág. {page_no}")


def main():
    with open(DATA, encoding="utf-8") as f:
        products = json.load(f)

    # agrupar respetando el orden de aparicion
    order = []
    groups = {}
    for p in products:
        if p["category"] not in groups:
            groups[p["category"]] = []
            order.append(p["category"])
        groups[p["category"]].append(p)

    c = canvas.Canvas(OUT, pagesize=A4)
    draw_cover(c)

    col_w = (W - 2 * MARGIN - (COLS - 1) * GAP) / COLS
    cell_img = col_w
    cell_h = cell_img + 3 + NAME_H
    page_no = 1

    for cat in order:
        items = groups[cat]
        band_y = draw_band(c, cat)
        top = band_y - 6 * mm
        bottom = MARGIN + 6 * mm
        rows = int((top - bottom + ROW_GAP) // (cell_h + ROW_GAP))
        rows = max(rows, 1)
        per_page = COLS * rows

        for i, p in enumerate(items):
            pos = i % per_page
            if i and pos == 0:
                draw_footer(c, page_no); page_no += 1
                c.showPage()
                band_y = draw_band(c, cat, cont=True)
                top = band_y - 6 * mm
            r = pos // COLS
            col = pos % COLS
            x = MARGIN + col * (col_w + GAP)
            y = top - r * (cell_h + ROW_GAP) - cell_img

            # marco de la celda
            c.setFillColorRGB(1, 1, 1)
            c.setStrokeColorRGB(0.90, 0.92, 0.94)
            c.roundRect(x, y - NAME_H, col_w, cell_img + NAME_H, 4, fill=1, stroke=1)

            if p["image"]:
                img_path = os.path.join(ROOT, p["image"].replace("/", os.sep))
                if os.path.exists(img_path):
                    pad = 4
                    c.drawImage(ImageReader(img_path), x + pad, y + pad,
                                col_w - 2 * pad, cell_img - 2 * pad,
                                preserveAspectRatio=True, mask='auto')
            else:
                c.setFillColorRGB(0.94, 0.96, 0.97)
                c.rect(x + 4, y + 4, col_w - 8, cell_img - 8, fill=1, stroke=0)
                c.setFillColorRGB(0.6, 0.66, 0.7)
                c.setFont("Helvetica-Oblique", 8)
                c.drawCentredString(x + col_w / 2, y + cell_img / 2, "Sin foto")

            # nombre
            c.setFillColorRGB(0.12, 0.16, 0.19)
            lines = wrap_name(c, p["name"], col_w - 8)
            ty = y - 4
            for ln in lines:
                ty -= 9
                c.drawCentredString(x + col_w / 2, ty, ln)

        draw_footer(c, page_no); page_no += 1
        c.showPage()

    c.save()
    kb = os.path.getsize(OUT) // 1024
    print(f"OK: {OUT} ({kb} KB, {page_no} páginas, {len(products)} productos)")


if __name__ == "__main__":
    main()
