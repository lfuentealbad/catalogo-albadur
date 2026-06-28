# Catálogo Albadur

Catálogo de productos en línea de **Sociedad Albadur** (distribuidora / venta al
por mayor). Sitio web estático con búsqueda, filtros por categoría y armado de
pedidos por WhatsApp o correo, más una versión en PDF imprimible.

🌐 **Sitio:** se publica con GitHub Pages (ver más abajo).
📄 **PDF:** [`Catalogo-Albadur.pdf`](Catalogo-Albadur.pdf) — 225 productos en 6 categorías.

![Albadur](assets/img/logo.svg)

---

## ¿Qué incluye?

- **`index.html`** — el sitio web (catálogo digital). No necesita servidor ni
  build: es HTML, CSS y JavaScript puro.
- **`assets/data/products.json`** — los 225 productos (nombre, categoría, foto).
  Es la única fuente de datos; el sitio y el PDF se generan desde aquí.
- **`assets/products/`** — las 223 fotos de producto (recortadas y normalizadas
  a 600×600 desde el catálogo original).
- **`Catalogo-Albadur.pdf`** — catálogo imprimible con portada y secciones por
  categoría.
- **`scripts/`** — utilidades en Python para regenerar los datos y el PDF.
- **`brand/`** — archivos originales del logotipo (SVG, EPS, JPG).

### Categorías

| Categoría | Productos |
|-----------|-----------|
| Confites | 123 |
| Despensa | 37 |
| Higiene Personal | 30 |
| Menaje | 24 |
| Refrescos | 8 |
| Librería | 3 |

---

## Activar los pedidos por WhatsApp

Por defecto los pedidos se envían por **correo** a `sociedadalbadur@gmail.com`.
Para habilitar también el botón de **WhatsApp**, edita la parte superior de
[`assets/js/app.js`](assets/js/app.js):

```js
const CONFIG = {
  whatsapp: "56912345678",   // número con código de país, sin + ni espacios
  email: "sociedadalbadur@gmail.com",
  businessName: "Sociedad Albadur",
};
```

> Ejemplo Chile: el número **+56 9 1234 5678** se escribe `"56912345678"`.
> Si lo dejas vacío, solo se muestra el envío por correo.

---

## Ver el sitio localmente

No requiere instalación. Para evitar problemas de carga del `products.json`,
ábrelo con un servidor local simple:

```bash
# en la carpeta del proyecto
python -m http.server 8000
# luego abre http://localhost:8000
```

---

## Actualizar el catálogo

### Cambiar un nombre o quitar un producto
Edita directamente [`assets/data/products.json`](assets/data/products.json).
Cada producto es:

```json
{ "id": 1, "name": "Alfajor Dorado 20u", "category": "Confites",
  "image": "assets/products/001-alfajor-dorado-20u.jpg" }
```

- Para un producto **sin foto**, usa `"image": null`.
- Las categorías válidas son las de la tabla de arriba.

### Agregar un producto con foto
1. Copia la foto en `assets/products/` (ideal cuadrada, fondo blanco).
2. Agrega su entrada en `products.json` apuntando a esa ruta.

### Regenerar el PDF
Después de modificar `products.json`:

```bash
pip install reportlab pillow pypdf
python scripts/build_pdf.py
```

### Regenerar todo desde el PDF original
El catálogo se construyó extrayendo las fotos del PDF original con
[`scripts/build_catalog.py`](scripts/build_catalog.py):

```bash
python scripts/build_catalog.py "ruta/al/Catalogo Albadur.pdf"
```

---

## Publicar en GitHub Pages

En el repositorio: **Settings → Pages → Build and deployment**, fuente
**Deploy from a branch**, rama `main`, carpeta `/ (root)`. En un par de minutos
el sitio queda disponible en `https://<usuario>.github.io/<repo>/`.

---

## Notas

- Dos productos no tienen foto en el catálogo original
  (*Azúcar D'Almacén granulada 1x10* y *Pila RayoVac AA 60u*); se muestran con un
  marcador "Foto no disponible".
- El pedido del cliente se guarda en el navegador (`localStorage`), así no se
  pierde si recarga la página.

© Sociedad Albadur
