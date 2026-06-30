#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Genera assets/data/destacados.json (los "más vendidos") cruzando el catálogo
con el "Informe de Local x Artículo" exportado desde Defontana.

El informe de Defontana se exporta como un .xls que en realidad es HTML.
Este script lo parsea, suma las unidades vendidas por artículo, lo cruza con
los productos del catálogo (assets/data/products.json) por similitud de nombre,
y escribe los IDs de los más vendidos ORDENADOS por ventas reales.

IMPORTANTе: en destacados.json NO se guardan cifras de venta (el archivo es
público); solo los IDs en orden de ranking.

Uso:
    python scripts/build_destacados.py "ruta/al/Informe de Ventas ... .xls" [TOP]
"""
import json, os, re, sys, unicodedata
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CATALOG = os.path.join(ROOT, "public", "assets", "data", "products.json")
OUT = os.path.join(ROOT, "public", "assets", "data", "destacados.json")

TOP_DEFAULT = 16
SCORE_MIN = 0.60

STOP = {"de","la","el","con","sin","por","y","sabor","sabores","u","x","display",
        "unidad","unidades","bolsa","gr","g","grs","ml","kg","kilo","cc","lt","l",
        "pack","caja","surtido","surtidos","surtida","variedades"}


def fix(s):
    return (s.replace("Ã¡","á").replace("Ã©","é").replace("Ã­","í")
             .replace("Ã³","ó").replace("Ãº","ú").replace("Ã±","ñ")
             .replace("ï¿½","").replace("�",""))


def parse_report(path):
    """Devuelve {nombre_articulo: unidades_vendidas} desde el informe HTML."""
    data = open(path, "rb").read().decode("latin-1", "replace")
    rows = re.findall(r"<tr>(.*?)</tr>", data, re.S)

    def cells(r):
        cs = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
        out = []
        for c in cs:
            c = re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").replace("&amp;", "&")
            out.append(re.sub(r"\s+", " ", c).strip())
        return out

    def num(s):
        s = (s or "").replace(".", "").replace(",", ".").strip()
        try: return float(s)
        except: return 0.0

    agg, current = {}, None
    for r in rows:
        c = cells(r)
        if len(c) < 7:
            continue
        art, doc, qty = c[1], c[2], c[3]
        if art.lower().startswith("total"):
            continue
        if art and "articulo" not in unicodedata.normalize("NFKD", art).encode("ascii","ignore").decode().lower():
            current = fix(art)
            agg.setdefault(current, 0.0)
        if current and doc:
            agg[current] += num(qty)
    return agg


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def tokens(s):
    out = []
    for t in norm(s).split():
        if t in STOP or re.fullmatch(r"\d+", t) or re.fullmatch(r"\d*x\d*", t):
            continue
        out.append(t)
    return set(out)


def score(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    jac = len(ta & tb) / len(ta | tb)
    seq = SequenceMatcher(None, norm(a), norm(b)).ratio()
    return 0.6 * jac + 0.4 * seq


def main():
    if len(sys.argv) < 2:
        sys.exit('Uso: python scripts/build_destacados.py "Informe ... .xls" [TOP]')
    report = sys.argv[1]
    top = int(sys.argv[2]) if len(sys.argv) > 2 else TOP_DEFAULT

    catalog = json.load(open(CATALOG, encoding="utf-8"))
    sales = parse_report(report)

    # Cada ARTÍCULO del ERP se asigna a UN SOLO producto del catálogo (su mejor
    # coincidencia). Así un artículo no infla varias entradas, y varios artículos
    # del ERP que correspondan al mismo producto del catálogo se suman.
    units = {p["id"]: 0.0 for p in catalog}
    for name, qty in sales.items():
        bp, bs = None, 0.0
        for p in catalog:
            sc = score(name, p["name"])
            if sc > bs:
                bs, bp = sc, p
        if bp and bs >= SCORE_MIN:
            units[bp["id"]] += qty

    by_id = {p["id"]: p for p in catalog}
    scored = [(pid, by_id[pid]["name"], q) for pid, q in units.items() if q > 0]
    scored.sort(key=lambda x: x[2], reverse=True)
    featured = scored[:top]
    ids = [s[0] for s in featured]

    json.dump(
        {"_comment": "Más vendidos REALES (orden por unidades vendidas), generado "
                     "desde el Informe de Local x Artículo de Defontana con "
                     "scripts/build_destacados.py. Solo IDs, sin cifras de venta.",
         "ids": ids},
        open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"OK: {len(ids)} destacados -> assets/data/destacados.json")
    for i, (pid, name, qty) in enumerate(featured, 1):
        print(f"  {i:2}. id={pid:<3} ({int(qty):>5} u)  {name}")


if __name__ == "__main__":
    main()
