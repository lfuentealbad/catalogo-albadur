/* ============================================================
   Albadur — catálogo de productos (sin dependencias)
   ============================================================ */

// --- Configuración editable ---------------------------------
// Para activar los pedidos por WhatsApp, escribe el número con
// código de país y SIN signos ni espacios. Ej: Chile +56 9 1234 5678
// se escribe "56912345678". Déjalo vacío para usar solo el correo.
const CONFIG = {
  whatsapp: "",                              // ej. "56912345678"
  email: "sociedadalbadur@gmail.com",
  businessName: "Sociedad Albadur",
};

const CATEGORY_COLORS = {
  "Confites":         "#994c9c",
  "Despensa":         "#faa633",
  "Higiene Personal": "#0075bf",
  "Menaje":           "#455560",
  "Refrescos":        "#00a68f",
  "Librería":         "#e31921",
  "Aseo y Hogar":     "#12a4c0",
  "Bolsas":           "#c9772f",
  "Otros":            "#6b7a85",
};
const CATEGORY_LABEL = {}; // las categorías ya vienen con su etiqueta correcta

const STORAGE_KEY = "albadur.order.v1";

const FEATURED_CAT = "__destacados__";

// --- Estado -------------------------------------------------
let PRODUCTS = [];
let FEATURED = new Set();   // ids de los productos más vendidos
let FEATURED_ORDER = [];    // mismos ids en orden de ventas (ranking real)
let activeCategory = "Todos";
let query = "";
let order = loadOrder(); // { [id]: qty }

// --- Utilidades ---------------------------------------------
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

function catLabel(cat) { return CATEGORY_LABEL[cat] || cat; }

function normalize(s) {
  return (s || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function loadOrder() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
  catch { return {}; }
}
function saveOrder() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(order)); } catch {}
}

function totalItems() {
  return Object.values(order).reduce((a, b) => a + b, 0);
}

// --- Carga de datos -----------------------------------------
async function init() {
  $("#year").textContent = new Date().getFullYear();
  setupContact();

  try {
    const res = await fetch("assets/data/products.json");
    PRODUCTS = await res.json();
  } catch (e) {
    $("#grid").innerHTML =
      '<p class="empty-state">No se pudo cargar el catálogo. Recarga la página.</p>';
    return;
  }

  // Más vendidos (opcional: si falta el archivo, simplemente no se muestra)
  try {
    const r = await fetch("assets/data/destacados.json");
    const d = await r.json();
    FEATURED_ORDER = (d.ids || []).filter(id => PRODUCTS.some(p => p.id === id));
    FEATURED = new Set(FEATURED_ORDER);
  } catch { FEATURED = new Set(); FEATURED_ORDER = []; }

  $("#stat-products").textContent = PRODUCTS.length;
  const cats = [...new Set(PRODUCTS.map(p => p.category))];
  $("#stat-cats").textContent = cats.length;

  buildFilters(cats);
  render();
  updateCartUI();
  setupEvents();
}

// --- Filtros ------------------------------------------------
function buildFilters(cats) {
  const filters = $("#filters");
  const counts = { "Todos": PRODUCTS.length };
  cats.forEach(c => counts[c] = PRODUCTS.filter(p => p.category === c).length);

  const all = ["Todos", ...cats];
  let html = all.map(c => `
    <button class="chip" role="tab" data-cat="${c}"
      aria-selected="${c === activeCategory}">
      ${catLabel(c)} <span class="chip-count">${counts[c]}</span>
    </button>`).join("");

  // Chip destacado "★ Más vendidos" al inicio (solo si hay destacados)
  if (FEATURED.size) {
    html = `
    <button class="chip chip-featured" role="tab" data-cat="${FEATURED_CAT}"
      aria-selected="${activeCategory === FEATURED_CAT}">
      ★ Más vendidos <span class="chip-count">${FEATURED.size}</span>
    </button>` + html;
  }
  filters.innerHTML = html;

  filters.addEventListener("click", e => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    activeCategory = chip.dataset.cat;
    $$(".chip", filters).forEach(c =>
      c.setAttribute("aria-selected", c.dataset.cat === activeCategory));
    render();
  });
}

// --- Render del grid ----------------------------------------
function filtered() {
  const q = normalize(query);
  const matchesQuery = p => !q || normalize(p.name).includes(q);

  // "Más vendidos": en orden de ventas reales (no orden de catálogo)
  if (activeCategory === FEATURED_CAT) {
    const byId = new Map(PRODUCTS.map(p => [p.id, p]));
    return FEATURED_ORDER.map(id => byId.get(id)).filter(p => p && matchesQuery(p));
  }

  return PRODUCTS.filter(p => {
    if (activeCategory !== "Todos" && p.category !== activeCategory) return false;
    return matchesQuery(p);
  });
}

function render() {
  const grid = $("#grid");
  const list = filtered();
  grid.setAttribute("aria-busy", "false");

  $("#empty-state").hidden = list.length > 0;
  const total = PRODUCTS.length;
  $("#result-summary").textContent = list.length === total
    ? `${total} productos`
    : `${list.length} de ${total} productos`;

  grid.innerHTML = list.map(cardHTML).join("");
}

function cardHTML(p) {
  const color = CATEGORY_COLORS[p.category] || "#455560";
  const inOrder = order[p.id] > 0;
  const media = p.image
    ? `<img src="${p.image}" alt="${escapeAttr(p.name)}" loading="lazy" />`
    : `<div class="card-noimg">
         <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18v14H3z M3 16l5-5 4 4 3-3 6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>
         <span>Foto no disponible</span>
       </div>`;

  const star = FEATURED.has(p.id)
    ? `<span class="fav-badge" title="Más vendido">★</span>` : "";

  return `
  <article class="card ${inOrder ? "in-order" : ""}" data-id="${p.id}">
    <div class="card-media">
      <span class="cat-tag" style="background:${color}">${catLabel(p.category)}</span>
      ${star}
      ${media}
    </div>
    <div class="card-body">
      <h3 class="card-name">${escapeHTML(p.name)}</h3>
      <div class="card-actions">${actionsHTML(p.id)}</div>
    </div>
  </article>`;
}

function actionsHTML(id) {
  const qty = order[id] || 0;
  if (qty <= 0) {
    return `<button class="add-btn" data-act="add" data-id="${id}">Agregar al pedido</button>`;
  }
  return `
    <div class="qty-control" role="group" aria-label="Cantidad">
      <button class="qty-btn" data-act="dec" data-id="${id}" aria-label="Quitar uno">−</button>
      <span class="qty-val">${qty}</span>
      <button class="qty-btn" data-act="inc" data-id="${id}" aria-label="Agregar uno">+</button>
    </div>`;
}

// --- Eventos del grid (delegación) --------------------------
function setupEvents() {
  $("#grid").addEventListener("click", e => {
    const btn = e.target.closest("[data-act]");
    if (!btn) return;
    const id = Number(btn.dataset.id);
    const act = btn.dataset.act;
    if (act === "add" || act === "inc") order[id] = (order[id] || 0) + 1;
    if (act === "dec") {
      order[id] = (order[id] || 0) - 1;
      if (order[id] <= 0) delete order[id];
    }
    saveOrder();
    refreshCard(id);
    updateCartUI();
    if (!$("#order-drawer").hidden) renderDrawer();
  });

  $("#search").addEventListener("input", e => { query = e.target.value; render(); });

  $("#cart-toggle").addEventListener("click", openDrawer);
  $("#drawer-close").addEventListener("click", closeDrawer);
  $("#drawer-backdrop").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && !$("#order-drawer").hidden) closeDrawer();
  });

  $("#clear-order").addEventListener("click", () => {
    if (!confirm("¿Vaciar todo el pedido?")) return;
    order = {}; saveOrder(); render(); updateCartUI(); renderDrawer();
  });
  $("#send-wa").addEventListener("click", sendWhatsApp);
  $("#send-email").addEventListener("click", sendEmail);
}

function refreshCard(id) {
  const card = $(`.card[data-id="${id}"]`);
  if (!card) return;
  card.classList.toggle("in-order", (order[id] || 0) > 0);
  $(".card-actions", card).innerHTML = actionsHTML(id);
}

// --- Carrito / contador -------------------------------------
function updateCartUI() {
  const n = totalItems();
  const badge = $("#cart-count");
  badge.textContent = n;
  badge.hidden = n === 0;
}

// --- Drawer -------------------------------------------------
function openDrawer() {
  $("#drawer-backdrop").hidden = false;
  $("#order-drawer").hidden = false;
  document.body.style.overflow = "hidden";
  renderDrawer();
  $("#drawer-close").focus();
}
function closeDrawer() {
  $("#drawer-backdrop").hidden = true;
  $("#order-drawer").hidden = true;
  document.body.style.overflow = "";
  $("#cart-toggle").focus();
}

function renderDrawer() {
  const body = $("#drawer-body");
  const foot = $("#drawer-foot");
  const ids = Object.keys(order).map(Number).filter(id => order[id] > 0);

  if (ids.length === 0) {
    foot.hidden = true;
    body.innerHTML = `
      <div class="order-empty">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6h15l-1.5 9h-12L6 6zM6 6L5 3H2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <p>Tu pedido está vacío.<br>Agrega productos desde el catálogo.</p>
      </div>`;
    return;
  }

  foot.hidden = false;
  body.innerHTML = ids.map(id => {
    const p = PRODUCTS.find(x => x.id === id);
    if (!p) return "";
    const media = p.image
      ? `<img src="${p.image}" alt="">`
      : `<div class="oi-noimg"></div>`;
    return `
      <div class="order-item" data-id="${id}">
        ${media}
        <div class="oi-main">
          <p class="oi-name">${escapeHTML(p.name)}</p>
          <button class="oi-remove" data-act="dec" data-id="${id}">Quitar</button>
        </div>
        <div class="qty-control" role="group" aria-label="Cantidad">
          <button class="qty-btn" data-act="dec" data-id="${id}" aria-label="Quitar uno">−</button>
          <span class="qty-val">${order[id]}</span>
          <button class="qty-btn" data-act="inc" data-id="${id}" aria-label="Agregar uno">+</button>
        </div>
      </div>`;
  }).join("");

  body.querySelectorAll("[data-act]").forEach(btn => {
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.id);
      const act = btn.dataset.act;
      if (act === "inc") order[id] = (order[id] || 0) + 1;
      else { order[id] = (order[id] || 0) - 1; if (order[id] <= 0) delete order[id]; }
      saveOrder(); refreshCard(id); updateCartUI(); renderDrawer();
    });
  });
}

// --- Generar pedido -----------------------------------------
function buildOrderText() {
  const ids = Object.keys(order).map(Number).filter(id => order[id] > 0);
  const name = $("#customer-name").value.trim();
  const notes = $("#customer-notes").value.trim();

  const lines = [];
  lines.push(`Pedido a ${CONFIG.businessName}`);
  if (name) lines.push(`Cliente: ${name}`);
  lines.push("");

  // Agrupado por categoría
  const byCat = {};
  ids.forEach(id => {
    const p = PRODUCTS.find(x => x.id === id);
    if (!p) return;
    (byCat[p.category] = byCat[p.category] || []).push(p);
  });
  Object.keys(byCat).forEach(cat => {
    lines.push(`*${catLabel(cat)}*`);
    byCat[cat].forEach(p => lines.push(`• ${order[p.id]} x ${p.name}`));
    lines.push("");
  });

  lines.push(`Total de ítems: ${totalItems()}`);
  if (notes) { lines.push(""); lines.push(`Notas: ${notes}`); }
  return lines.join("\n");
}

function sendWhatsApp() {
  if (totalItems() === 0) return;
  const text = encodeURIComponent(buildOrderText());
  window.open(`https://wa.me/${CONFIG.whatsapp}?text=${text}`, "_blank");
}

function sendEmail() {
  if (totalItems() === 0) return;
  const subject = encodeURIComponent(`Pedido — ${CONFIG.businessName}`);
  const body = encodeURIComponent(buildOrderText());
  window.location.href = `mailto:${CONFIG.email}?subject=${subject}&body=${body}`;
}

// --- Contacto -----------------------------------------------
function setupContact() {
  if (CONFIG.whatsapp) {
    const wa = $("#contact-wa");
    wa.href = `https://wa.me/${CONFIG.whatsapp}`;
    wa.hidden = false;
    wa.target = "_blank";
    $("#send-wa").hidden = false;
  }
  $("#contact-email").href = `mailto:${CONFIG.email}`;
}

// --- Escapado -----------------------------------------------
function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHTML(s); }

document.addEventListener("DOMContentLoaded", init);
