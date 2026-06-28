#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extrae las fotos de producto del catalogo PDF original de Albadur y genera
el archivo assets/data/products.json que alimenta el sitio web.

Uso:
    python scripts/build_catalog.py "ruta/al/Catalogo Albadur.pdf"

Las fotos se normalizan a un lienzo cuadrado blanco de 600x600 para que las
tarjetas del catalogo se vean uniformes.
"""
import io
import json
import os
import sys
import unicodedata

from pypdf import PdfReader
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRODUCTS_DIR = os.path.join(ROOT, "assets", "products")
DATA_DIR = os.path.join(ROOT, "assets", "data")

BACKGROUND_SIZE = (1275, 1650)  # imagen de fondo de pagina (se ignora)
CANVAS = 600

# Categoria por numero de pagina (1-indexado, como aparece en el PDF)
CATEGORY_BY_PAGE = {}
for p in range(2, 13):
    CATEGORY_BY_PAGE[p] = "Confites"
for p in (13, 14, 15):
    CATEGORY_BY_PAGE[p] = "Higiene Personal"
CATEGORY_BY_PAGE[16] = "Refrescos"
for p in (17, 18, 19, 20):
    CATEGORY_BY_PAGE[p] = "Despensa"
for p in (21, 22):
    CATEGORY_BY_PAGE[p] = "Menaje"
CATEGORY_BY_PAGE[23] = "Libreria"

# Nombres de producto por pagina, en el mismo orden que las fotos.
# (Curado a mano desde el texto del PDF, corrigiendo erratas evidentes.)
NAMES_BY_PAGE = {
    2: [
        "Alfajor Dorado 20u",
        "Alfajor Panchote",
        "Barra caramelo y mani Rambo 24u",
        "Biscocho Chocman Black x32",
        "Bandeja Cuchufli Blanco x90",
        "Bandeja Cuchufli banado Chocolate x50",
        "Biscocho Chocman Clasico x32",
        "Bolitas Crocantes Asterix 20u",
        "Bombon Bon o Bon Blanco 30u",
        "Bombones de chocolate corazon 180gr",
        "Bombon Bon o Bon Chocolate 30u",
        "Bombon corazon 8u Dorado",
    ],
    3: [
        "Bombon corazon 8u Rojo",
        "Bombon corazon 3u Dorado - Rojo",
        "Bombon corazon 5u",
        "Bon Bon Bum fresa 24u",
        "Bon Bon Bum Mistery 24u",
        "Bon Bon Bum sabor uva 24u",
        "Bon Bon Bum sabores surtidos 24u",
        "Bon Bon Bum surtido tropical 24u",
        "Candy Maquinita x24",
        "Caramelo Alka cristal menta 100u",
        "Caluga Suny clasica bolsa 400gr",
        "Caluga Old England Toffee 450gr",
    ],
    4: [
        "Caluga Old England Toffee Mint 450gr",
        "Caramelo Alka Ice cereza 100u",
        "Caramelo Alka Ice miel 100u",
        "Caramelo Alka mentol 100u",
        "Caramelo Full limon 24u",
        "Caramelo Full Masti Crunch 24u",
        "Caramelo Mentitas 24u",
        "Caramelo Mentitas Masti Crunch 24u",
        "Caramelo Surtido Arbolito x100",
        "Caramelos masticables Max frutas con crema",
        "Chicle Bigtime Acid Blueberry 20u",
        "Chicle Bigtime Aqua 20u",
    ],
    5: [
        "Chicle Bigtime Frutilla Acida 20u",
        "Chicle Bigtime Menta 20u",
        "Chicle Bigtime Refrescante 20u",
        "Chicle Bigtime Sandia 20u",
        "Chicle Bigtime Strong 20u",
        "Chicle Bolon 100u",
        "Chicle globo Grosso 150u",
        "Chicle Grosso sabor menta 100u",
        "Chicle Grosso sabor sandia 100u",
        "Chicle Rollo sabores surtidos 30u",
        "Chicle Sandia 100u",
        "Chicle Splot Acid 120u",
    ],
    6: [
        "Chocolate Capri sabor almendra 24u",
        "Chocolate Capri sabor frutilla 24u",
        "Chocolate Verona sabor chocolate",
        "Chupete Bowling Cream 24u",
        "Chupete Yogueta surtida 20u",
        "Chupetines Pico Dulce 53u",
        "Confite Chubi 24u",
        "Doble Chirlito 40u",
        "Dulce Tucrema 48u",
        "Enojones sabor chirimoya alegre x10u",
        "Frugele gomitas 100u",
        "Frutos Leblon 60u",
    ],
    7: [
        "Galleta de champana Gullon 200g",
        "Galleta Tableton",
        "Galleta Fruna 1x32",
        "Galleta Nonitas 55g",
        "Galleta sabor chocolate 140g",
        "Galletas de mantequilla estilo danes",
        "Galletas sabor limon 140g",
        "Galletitas Dulces Fruna sabor Chocolate 500g",
        "Gato Encerrado sabor chocolate x10u",
        "Gomitas acidas Loop 20u",
        "Gomitas Amberries 20u",
        "Gomitas Flipy 20u",
    ],
    8: [
        "Gomitas Hamburguesa 36u",
        "Gomitas Mini Hot Dog 36u",
        "Gomitas sabor frutillas a la crema 20u",
        "Huevo Dino Sorpresa x24 armables",
        "Huevo Dino Sorpresa x30",
        "Huevo sorpresa Car x24",
        "Huevo sorpresa nino-nina x24",
        "Lenguicido XL sabor frutilla 24u",
        "Lenguicido XL sabor manzana 24u",
        "Malvavisco Oba Oba 30u",
        "Mani Choc chocolate 20u",
        "Mani Choc confitado 20u",
    ],
    9: [
        "Mani Tifany's 20u",
        "Marshmallows Cubanitos",
        "Marshmallows Run-Run sabor vainilla",
        "Mini jaleas sabores surtidos 50u",
        "Minitorta selva negra 20u",
        "Minitorta Tortazo 20u",
        "Monedas sabor Chocolate x50",
        "Oblea Bachata sabor coco 20u",
        "Oblea Bachata sabor cremino 20u",
        "Oblea Kilate 20u",
        "Pack Milo en sobre 28g 10u",
        "Paleta corazon cereza 24u",
    ],
    10: [
        "Paleta escobita azul 24u",
        "Paleta Lollipop boquita 24u",
        "Paleta Loly Choc 24u",
        "Palito Palo Loco 30u",
        "Polvo Mabu Explota X4 30u",
        "Super 8 24u",
        "Turron de mani 28u",
        "Galleta Palmerita Conquista 300gr",
        "Galleta Media Tarde 100gr",
        "Chocolate Costa Rama 115gr",
        "Bombon Mabu rectangular 12 pcs",
        "Bocadito Membrillo 300g",
    ],
    11: [
        "Chocolate Vizzio 120g",
        "Galleta Suny 120g",
        "Galleta Surtidas 400g",
        "Huevo grande 50u Mabu",
        "Barra de chocolate Sahne-Nuss 250g",
        "Puro de chocolate Fruna",
        "Choky crema 20u",
        "Trufas de chocolate Amore",
        "Candy Raton globo 30u",
        "Candy Spray 24u",
        "Palo Loco 30u",
        "Bombon Lexus 1 kilo",
    ],
    12: [
        "Galleta Bon o Bon 95gr",
        "Galleta Donuts variedades",
        "Donas Fruna 1200g",
    ],
    13: [
        "Acondicionador Ballerina Bajopoo Micelar 750ml",
        "Acondicionador Ballerina Color Ideal 750ml",
        "Acondicionador Ballerina Detox 750ml",
        "Colgate triple accion 50g 6u",
        "Gillette Prestobarba 2 Ultragrip 14u",
        "Gillette Prestobarba 3 Confort gel 20u",
        "Maquina de Afeitar Wilkinson doble hoja 12u",
        "Maquina de Afeitar Xtreme 3 Hawaiian Tropic",
        "Maquina de Afeitar Xtreme 3 piel normal",
        "Maquina de Afeitar Xtreme 3 sensible",
        "Maquina de Afeitar Xtreme 3 Eco",
        "Panal desechable Babysec Premium G",
    ],
    14: [
        "Panal desechable Babysec Premium M",
        "Panal desechable Babysec Premium XG",
        "Panal desechable Babysec Premium XXG",
        "Panuelos desechables Elite triple hoja x18",
        "Shampoo Ballerina Accion Antioxidante 750ml",
        "Shampoo Ballerina Accion Antioxidante 900ml",
        "Shampoo Ballerina Bajopoo 900ml",
        "Shampoo Ballerina Detox 900ml",
        "Shampoo Head & Shoulders limpieza renovadora 10ml x24",
        "Toalla de bano 90x180",
        "Toalla femenina Kotex normal con alas",
        "Toalla femenina Mimosa normal con alas",
    ],
    15: [
        "Toalla femenina Parati nocturna con alas",
        "Toalla femenina Parati normal con alas",
        "Toalla femenina Parati Apositos TU",
        "Toalla femenina Parati Apositos XG",
        "Toalla femenina Cotidian Apositos",
        "Toalla femenina Blu Apositos",
    ],
    16: [
        "Jugo en polvo Sprim durazno 10u",
        "Jugo en polvo Sprim frambuesa 10u",
        "Jugo en polvo Sprim melon tuna 10u",
        "Jugo en polvo Sprim multifrut 10u",
        "Jugo en polvo Sprim naranja 10u",
        "Jugo en polvo Sprim papaya 10u",
        "Jugo en polvo Sprim pina 10u",
        "Jugo en polvo Zuko pina 10u",
    ],
    17: [
        "Aceite comestible maravilla 5 Litros Coliseo",
        "Aceite comestible vegetal D'Almacen 900ml",
        "Alimento Milo bolsa 210g",
        "Arroz grano largo ancho Grado 2 Valle de Oro 1x10",
        "Azucar D'Almacen blanca granulada 1x10",   # SIN FOTO
        "Azucar Iansa blanca granulada 1,5kg",
        "Cafe Nescafe Black Roast 50g",
        "Cafe Nescafe Tradicion 50g",
        "Caldo sabor Carne 48u",
        "Caldo sabor Costilla 48u",
        "Caldo sabor Gallina 48u",
        "Colacao en polvo sabor chocolate 330g",
    ],
    18: [
        "Crema de leche Bravo Cream",
        "Fideo Fettuccine 88 400g Carozzi",
        "Fideo Tallarines 87 400g Carozzi",
        "Fideos Espirales 400g Carozzi",
        "Fideos Rigatoni 400g Carozzi",
        "Jurel Colorado",
        "Jurel en agua San Marcos",
        "Ketchup Don Juan sobre 100g 18u",
        "Levadura Collico seca en sobres 10g 10u",
        "Levadura Lefersa seca en sobres 10g 10u",
        "Levadura seca instantanea 500g",
        "Mani con pasas 180g",
    ],
    19: [
        "Manjar Calo 400g",
        "Mayonesa Hellmann's 24u de 93g",
        "Mostaza Don Juan sobre 100g 18u",
        "Nescafe Tradicion 96u de 1,8g",
        "Para Uno Caracoquesos",
        "Para Uno Espirales Bolognesa",
        "Polvos de hornear Imperial 1x50",
        "Salsa de tomate Italiana Aconcagua 200g",
        "Sucedaneo jugo de limon 500ml Don Juan x12u",
        "Vinagre Blanco Don Juan 250cc x15",
        "Durazno en cubitos Wasil 380gr",
        "Durazno en cubitos Regimel 380gr",
    ],
    20: [
        "Yerba Mate con palo Caballo Blanco 5kg",
    ],
    21: [
        "Ampolleta HaloBright Classic 42W 10u",
        "Ampolleta HaloBright Classic 70W 10u",
        "Ampolleta RedPower 42W luz calida",
        "Ampolleta RedPower 70W luz calida",
        "Bombilla metalica 6 piezas",
        "Copa Versalles Vino Tinto 6x300cc",
        "Cuchara de te 6 piezas",
        "Encendedores Ronson Clearlite x20",
        "Encendedores Ronson con disenos x20",
        "Fosforo de seguridad Pavo Real 1x10",
        "Fosforo de seguridad Talisman x10",
        "Juego de colador plastico 4 piezas",
    ],
    22: [
        "Pegamento Super Glue Chemmer 12u",
        "Pila Duracell AA x12",
        "Pila Duracell AAA x6",
        "Pila Duracell C2 x2",
        "Pila RayoVac AA 48u",
        "Pila RayoVac AA 60u",   # SIN FOTO
        "Pila RayoVac AAA 30u",
        "Pila RayoVac D 24u",
        "Vaso Monterrey Rocks 6x296cc",
        "Vasos altos Slice 6x470cc",
        "Vela Antorcha 4u",
        "Venditas Standard CureBand x100",
    ],
    23: [
        "Lapiz BIC cristal Azul x50",
        "Lapiz BIC cristal Negro x50",
        "Rollo de papel 20cm",
    ],
}

# Productos sin foto en el PDF (indice 0-based dentro de su pagina).
MISSING_IMAGE = {
    17: {4},   # Azucar D'Almacen blanca granulada 1x10
    22: {5},   # Pila RayoVac AA 60u
}


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower()
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_/":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def square(img):
    img = img.convert("RGB")
    img.thumbnail((CANVAS, CANVAS), Image.LANCZOS)
    canvas = Image.new("RGB", (CANVAS, CANVAS), (255, 255, 255))
    canvas.paste(img, ((CANVAS - img.width) // 2, (CANVAS - img.height) // 2))
    return canvas


def main():
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.expanduser("~"), "Downloads", "Catalogo Albadur.pdf"
    )
    if not os.path.exists(pdf_path):
        sys.exit("No se encontro el PDF: " + pdf_path)

    os.makedirs(PRODUCTS_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    reader = PdfReader(pdf_path)
    products = []
    pid = 0
    used_slugs = set()

    for page_no in sorted(NAMES_BY_PAGE):
        names = NAMES_BY_PAGE[page_no]
        category = CATEGORY_BY_PAGE[page_no]
        missing = MISSING_IMAGE.get(page_no, set())

        page = reader.pages[page_no - 1]
        imgs = [im for im in page.images if im.image.size != BACKGROUND_SIZE]

        expected_imgs = len(names) - len(missing)
        if len(imgs) != expected_imgs:
            print(f"  AVISO pagina {page_no}: {len(imgs)} fotos, se esperaban "
                  f"{expected_imgs} ({len(names)} nombres)")

        img_iter = iter(imgs)
        for idx, name in enumerate(names):
            pid += 1
            slug = slugify(name)
            if slug in used_slugs:
                slug = f"{slug}-{pid}"
            used_slugs.add(slug)

            image_file = None
            if idx not in missing:
                try:
                    im = next(img_iter)
                    out_name = f"{pid:03d}-{slug}.jpg"
                    square(im.image).save(
                        os.path.join(PRODUCTS_DIR, out_name), "JPEG", quality=82
                    )
                    image_file = f"assets/products/{out_name}"
                except StopIteration:
                    image_file = None

            products.append({
                "id": pid,
                "name": name,
                "category": category,
                "image": image_file,
            })

    with open(os.path.join(DATA_DIR, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    cats = {}
    for p in products:
        cats[p["category"]] = cats.get(p["category"], 0) + 1
    print(f"OK: {len(products)} productos -> assets/data/products.json")
    for c, n in cats.items():
        print(f"  {c}: {n}")
    no_img = [p["name"] for p in products if not p["image"]]
    print(f"Sin foto ({len(no_img)}): {', '.join(no_img)}")


if __name__ == "__main__":
    main()
