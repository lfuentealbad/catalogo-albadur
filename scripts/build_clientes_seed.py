#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Genera el SQL para cargar la lista blanca de clientes (RUT + nombre) en la base
D1, a partir del Excel "Lista de Clientes" exportado desde Defontana.

⚠️ La salida contiene DATOS PERSONALES (RUT y nombres). Se escribe en
   .data/seed_clientes.local.sql, que está en .gitignore y NUNCA se sube al repo.
   Solo se usa para cargar la base D1 (local y remota) con wrangler.

Uso:
    python scripts/build_clientes_seed.py "ruta/al/Lista de Clientes.xlsx"
"""
import os, re, sys, unicodedata
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, ".data")
OUT = os.path.join(OUT_DIR, "seed_clientes.local.sql")


def norm_rut(r):
    # sin puntos/espacios, K mayúscula, con guión, SIN ceros a la izquierda
    r = str(r).upper().replace(".", "").replace(" ", "").strip()
    if "-" not in r and len(r) >= 2:
        r = r[:-1] + "-" + r[-1]
    num, _, dv = r.partition("-")
    num = num.lstrip("0") or "0"
    return f"{num}-{dv}"


def clean_name(n):
    n = str(n).strip()
    # arregla acentos rotos típicos del export latin-1
    n = (n.replace("Ã¡", "á").replace("Ã©", "é").replace("Ã­", "í")
           .replace("Ã³", "ó").replace("Ãº", "ú").replace("Ã±", "ñ"))
    n = n.replace("�", "").replace("�", "")
    n = re.sub(r"\s+", " ", n).strip()
    return n.replace("'", "''")  # escape SQL


def main():
    if len(sys.argv) < 2:
        sys.exit('Uso: python scripts/build_clientes_seed.py "Lista de Clientes.xlsx"')
    src = sys.argv[1]

    df = pd.read_excel(src, header=1, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    col_rut, col_nom, col_est = df.columns[0], df.columns[2], df.columns[3]

    seen, rows = set(), []
    for _, r in df.iterrows():
        rut = norm_rut(r[col_rut])
        estado = str(r[col_est]).strip()
        if not re.fullmatch(r"\d{6,8}-[0-9K]", rut):   # RUT con formato válido
            continue
        if rut in ("0-0",) or rut in seen:
            continue
        if estado.lower() != "activo":
            continue
        seen.add(rut)
        rows.append((rut, clean_name(r[col_nom]), estado))

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- GENERADO automáticamente. DATOS PERSONALES — no subir al repo.\n")
        f.write("DELETE FROM clientes;\n")
        for rut, nombre, estado in rows:
            f.write(f"INSERT INTO clientes (rut, nombre, estado) VALUES "
                    f"('{rut}', '{nombre}', '{estado}');\n")

    print(f"OK: {len(rows)} clientes -> {OUT}")
    print("   (archivo en .gitignore; no se sube al repo)")


if __name__ == "__main__":
    main()
