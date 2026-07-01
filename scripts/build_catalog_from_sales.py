#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reconstruye el catálogo (public/assets/data/products.json) a partir del
"Informe Consolidado x Artículo" de Defontana de los últimos 90 días.

- Extrae los productos vendidos + cantidades.
- Limpia nombres y los clasifica en categorías por palabras clave.
- Reutiliza las fotos reales ya conseguidas (match por nombre con el catálogo
  anterior) donde coincidan; el resto queda sin foto (image=null) hasta buscarla.
- Recalcula los "más vendidos" (destacados) con estas ventas de 90 días.

Uso:  python scripts/build_catalog_from_sales.py "Informe ... .xls"
"""
import json, os, re, sys, unicodedata
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "public", "assets", "data")
CATALOG = os.path.join(DATA, "products.json")
DEST = os.path.join(DATA, "destacados.json")

# ---- categorización por palabras clave (orden de prioridad) ----
CATS = [
 ("Aseo y Hogar", ["cloro","lavaloza","lava loza","detergente","omo","magistral","quix","impeke",
    "esponja","virutilla","desinfectante","limpiador","jabon liquido","cera piso","cif","escoba",
    "pala","trapero","confort","papel higienico","toalla nova","nova 70","toalla de mano",
    "servilleta","agua oxigenada","cloro gel","antisarro","lustramueble","insecticida","paño"]),
 ("Higiene Personal", ["shampoo","acondicionador","colgate","pasta dental","cepillo dental",
    "gillette","prestobarba","presto barba","afeitar","schick","wilkinson","panal","pañal",
    "babysec","toalla higenica","toalla higienica","toalla femenina","toalla hig","aposito",
    "kotex","parati","mimosa","cotidian","nosotras","always","lady sof","protector","panuelo",
    "jabon","desodorante","speed stick","pinza depilatoria","algodon","cotonito","hisopo",
    "mascarilla","toallitas","humedas","cotton","tintura","tinte","balsamo","nivea","colonia",
    "mamadera","crema corporal","cofarena","cafarena"]),
 ("Refrescos", ["jugo","sprim","zuko","livean","bebida","coca cola","serrana","cachantun",
    "agua mineral","nectar","refresco","gaseosa","gatorade","in liquido"]),
 ("Despensa", ["aceite","harina","arroz","azucar","fideo","tallarin","espiral","rigatoni",
    "pastina","cafe","nescafe","leche","crema espesa","crema colun","crema nestle","crema de leche",
    "manjar","mayonesa","ketchup","mostaza","salsa","pomarola","aji","atun","jurel","chorito",
    "sardina","conserva","durazno","mermelada","yerba","te ","tea","emblem","caldo","sopa",
    "maruchan","ramen","colacao","milo","levadura","polvos de hornear","vinagre","poroto",
    "lenteja","garbanzo","avena","cereal","sal ","mani con pasas","fecula","chancaca","imperial",
    "gelatina","postre","maiz","pan de","condimento","comino","oregano"]),
 ("Librería", ["lapiz","lipiz","bic","cuaderno","block","goma de borrar","goma miga","regla",
    "tijera","corchete","clip","resma","retma","calculadora","plumon","marcador","sacapunta",
    "tempera","cartulina","pegamento en barra","cola fria","faber","eifel","pincel","scotch",
    "cinta de embalaje","cinta embalaje","papel de regalo","papel regalo","sobre carta"]),
 ("Menaje", ["vaso","copa","jarra","olla","tetera","tazon","asadera","wol enlozado","sarten",
    "plato","cuchara","tenedor","cuchillo","colador","pila","bateria","ampolleta","foco",
    "encendedor","fosforo","vela","pegamento","super glue","bombilla","guante","balde","tineta",
    "cotillon","globo","desechable","fuente","budinera","budin","juego de ollas","manga vasos",
    "gradua","termo","destapador","abrelata","curita","venditas","cureband","parche","enlozad"]),
 ("Confites", ["chocolate","galleta","caramelo","chicle","bombon","alfajor","chupete","chupetin",
    "gomita","gomaton","gummy","mani","oblea","turron","marshmallow","malvavisco","super 8","dulce",
    "confite","chocman","caluga","paleta","moneda","huevo","torta","bocadito","membrillo","frugele",
    "masticable","cuchufli","biscocho","choky","trufa","candy","palo loco","frac","triton","trencito",
    "nik","costa","orly","serranita","tableton","kilate","bachata","asterix","aterix","leblon","frutos",
    "papas","kryspo","marco polo","doritos","ramitas","cheezels","suny","enojones","chirlito","lengu",
    "chubi","tucrema","yogueta","pico dulce","run run","tifany","bon o bon","mabu","vizzio","gatolate",
    "halls","golazo","coquet","didi","bolon","full ambrosoli","arbolito","churrazo","chispote","sufles",
    "cubanito","conejo","lollipop","figura platano","mentitas","sustancias","jalea","honguito","mega bolon",
    "de todito","maiz inflado","gatolate","sobre imperial"]),
 ("Bolsas", ["bolsa","manga plastico","manga vaso","film","alusa","clean pack","basura"]),
]

def clean_name(n):
    n = (n.replace("Ã¡","á").replace("Ã©","é").replace("Ã­","í").replace("Ã³","ó")
           .replace("Ãº","ú").replace("Ã±","ñ").replace("ï¿½","").replace("�",""))
    n = re.sub(r"\s+", " ", n).strip()
    letters = [c for c in n if c.isalpha()]
    # Si viene TODO en mayúsculas o todo en minúsculas -> Title Case suave
    if letters and (all(c.isupper() for c in letters) or all(c.islower() for c in letters)):
        small = {"de","del","con","sin","x","y","la","el","los","las","al","en","gr","ml","kg","cc","lt"}
        words = []
        for w in n.split():
            lw = w.lower()
            if re.match(r"^\d", w) or lw in small:
                words.append(lw if lw in small else w)
            else:
                words.append(w.capitalize())
        n = " ".join(words)
        if n[:1].islower(): n = n[0].upper() + n[1:]
    return n

def norm(s):
    return re.sub(r"[^a-z0-9 ]"," ",unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower())

def categorize(name):
    low = " " + norm(name) + " "
    for cat, kws in CATS:
        for kw in kws:
            if norm(kw) in low:
                return cat
    return "Otros"

STOP = {"de","la","el","con","sin","x","y","sabor","sabores","u","unidad","unidades","bolsa",
        "gr","g","ml","kg","cc","display","pack"}
def tokens(s):
    return {t for t in norm(s).split() if t and t not in STOP and not re.fullmatch(r"\d+|\d*x\d*", t)}
def match_score(a,b):
    ta,tb = tokens(a),tokens(b)
    if not ta or not tb: return 0.0
    return 0.6*len(ta&tb)/len(ta|tb) + 0.4*SequenceMatcher(None,norm(a),norm(b)).ratio()

def parse_report(path):
    data = open(path,"rb").read().decode("latin-1","replace")
    rows = re.findall(r"<tr>(.*?)</tr>", data, re.S)
    def cells(r):
        cs = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
        return [re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",c).replace("&nbsp;"," ").replace("&amp;","&")).strip() for c in cs]
    def num(s):
        s=(s or "").replace(".","").replace(",",".").strip()
        try: return float(s)
        except: return 0.0
    agg, cur = {}, None
    for r in rows:
        c = cells(r)
        if len(c) < 3: continue
        art, doc, qty = c[0], c[1], c[2]
        if art.lower().startswith("total"): continue
        if art and "articulo" not in norm(art):
            cur = art; agg.setdefault(cur, 0.0)
        if cur and doc: agg[cur] += num(qty)
    return agg

def main():
    report = sys.argv[1]
    sales = parse_report(report)

    # catálogo anterior (para reutilizar fotos por match de nombre)
    old = json.load(open(CATALOG, encoding="utf-8"))
    old_with_img = [p for p in old if p.get("image")]

    items = []
    for raw, qty in sales.items():
        name = clean_name(raw)
        cat = categorize(name)
        # buscar foto existente
        bi, bs = None, 0.0
        for op in old_with_img:
            sc = match_score(name, op["name"])
            if sc > bs: bs, bi = sc, op
        image = bi["image"] if (bi and bs >= 0.62) else None
        items.append({"name": name, "category": cat, "qty": qty, "image": image})

    # ordenar por categoría (según CATS) y dentro por ventas desc
    order = [c for c,_ in CATS] + ["Otros"]
    items.sort(key=lambda p: (order.index(p["category"]) if p["category"] in order else 99, -p["qty"]))

    products, dest = [], []
    for i, it in enumerate(items, 1):
        products.append({"id": i, "name": it["name"], "category": it["category"], "image": it["image"]})

    json.dump(products, open(CATALOG,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

    # destacados: top 16 por ventas 90d que tengan foto
    top = sorted([it for it in items if it["image"]], key=lambda p:-p["qty"])[:16]
    top_ids = [products[items.index(t)]["id"] for t in top]
    json.dump({"_comment":"Más vendidos reales (ventas 90 días). Solo IDs.","ids":top_ids},
              open(DEST,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

    # stats
    from collections import Counter
    cc = Counter(p["category"] for p in products)
    conimg = sum(1 for p in products if p["image"])
    print(f"CATÁLOGO NUEVO: {len(products)} productos | con foto reutilizada: {conimg} | sin foto: {len(products)-conimg}")
    for c in order:
        if cc.get(c): print(f"  {c}: {cc[c]}")

if __name__ == "__main__":
    main()
