/**
 * Worker de Albadur.
 * - Sirve el catálogo estático (binding ASSETS).
 * - Expone /api/auth/* para el login de clientes validado por RUT contra la
 *   lista importada de Defontana (tabla `clientes` en D1).
 *
 * Sin dependencias externas: hashing con Web Crypto (PBKDF2).
 */

const SESSION_DAYS = 30;
const PBKDF2_ITER = 100000;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/api/")) {
      try {
        return await handleApi(request, env, url);
      } catch (err) {
        return json({ ok: false, error: "Error interno" }, 500);
      }
    }
    // todo lo demás: archivos estáticos del catálogo
    return env.ASSETS.fetch(request);
  },
};

async function handleApi(request, env, url) {
  const p = url.pathname;
  if (p === "/api/auth/check-rut" && request.method === "POST") return checkRut(request, env);
  if (p === "/api/auth/register" && request.method === "POST") return register(request, env);
  if (p === "/api/auth/login" && request.method === "POST") return login(request, env);
  if (p === "/api/auth/logout" && request.method === "POST") return logout(request, env);
  if (p === "/api/auth/me" && request.method === "GET") return me(request, env);
  return json({ ok: false, error: "No encontrado" }, 404);
}

/* ---------------- Endpoints ---------------- */

// ¿El RUT es un cliente válido? ¿ya tiene cuenta?
async function checkRut(request, env) {
  const { rut } = await readJson(request);
  const r = normalizeRut(rut);
  if (!r) return json({ ok: false, error: "RUT inválido" }, 400);

  const cli = await env.DB.prepare("SELECT nombre FROM clientes WHERE rut = ?")
    .bind(r).first();
  if (!cli) {
    return json({ ok: true, exists: false });
  }
  const acc = await env.DB.prepare("SELECT rut FROM cuentas WHERE rut = ?")
    .bind(r).first();
  return json({ ok: true, exists: true, nombre: cli.nombre, hasAccount: !!acc });
}

// Crear cuenta (solo si el RUT está en la lista y aún no tiene cuenta)
async function register(request, env) {
  const { rut, password, email } = await readJson(request);
  const r = normalizeRut(rut);
  if (!r) return json({ ok: false, error: "RUT inválido" }, 400);
  if (!password || String(password).length < 6)
    return json({ ok: false, error: "La contraseña debe tener al menos 6 caracteres" }, 400);

  const cli = await env.DB.prepare("SELECT nombre FROM clientes WHERE rut = ?")
    .bind(r).first();
  if (!cli)
    return json({ ok: false, error: "No encontramos tu RUT como cliente. Contáctanos." }, 403);

  const exists = await env.DB.prepare("SELECT rut FROM cuentas WHERE rut = ?")
    .bind(r).first();
  if (exists)
    return json({ ok: false, error: "Ya existe una cuenta con este RUT. Inicia sesión." }, 409);

  const hash = await hashPassword(String(password));
  const now = new Date(env.__now || Date.now()).toISOString();
  await env.DB.prepare("INSERT INTO cuentas (rut, password_hash, email, creado) VALUES (?,?,?,?)")
    .bind(r, hash, email ? String(email).slice(0, 120) : null, now).run();

  return startSession(env, r, cli.nombre);
}

async function login(request, env) {
  const { rut, password } = await readJson(request);
  const r = normalizeRut(rut);
  if (!r) return json({ ok: false, error: "RUT inválido" }, 400);

  const acc = await env.DB.prepare(
    "SELECT c.password_hash AS h, cl.nombre AS nombre FROM cuentas c " +
    "JOIN clientes cl ON cl.rut = c.rut WHERE c.rut = ?").bind(r).first();
  if (!acc) return json({ ok: false, error: "RUT o contraseña incorrectos" }, 401);

  const ok = await verifyPassword(String(password || ""), acc.h);
  if (!ok) return json({ ok: false, error: "RUT o contraseña incorrectos" }, 401);

  return startSession(env, r, acc.nombre);
}

async function me(request, env) {
  const token = getCookie(request, "sid");
  if (!token) return json({ ok: true, auth: false }, 200);
  const row = await env.DB.prepare(
    "SELECT s.rut AS rut, cl.nombre AS nombre, s.expira AS expira FROM sesiones s " +
    "JOIN clientes cl ON cl.rut = s.rut WHERE s.token = ?").bind(token).first();
  const now = Number(env.__now || Date.now());
  if (!row || Number(row.expira) < now) {
    if (row) await env.DB.prepare("DELETE FROM sesiones WHERE token = ?").bind(token).run();
    return json({ ok: true, auth: false }, 200);
  }
  return json({ ok: true, auth: true, rut: row.rut, nombre: row.nombre });
}

async function logout(request, env) {
  const token = getCookie(request, "sid");
  if (token) await env.DB.prepare("DELETE FROM sesiones WHERE token = ?").bind(token).run();
  return new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { "content-type": "application/json", "set-cookie": clearCookie() },
  });
}

/* ---------------- Sesión ---------------- */

async function startSession(env, rut, nombre) {
  const token = crypto.randomUUID() + crypto.randomUUID().replace(/-/g, "");
  const now = Number(env.__now || Date.now());
  const expira = now + SESSION_DAYS * 24 * 3600 * 1000;
  await env.DB.prepare("INSERT INTO sesiones (token, rut, expira) VALUES (?,?,?)")
    .bind(token, rut, expira).run();
  return new Response(JSON.stringify({ ok: true, rut, nombre }), {
    status: 200,
    headers: { "content-type": "application/json", "set-cookie": sessionCookie(token) },
  });
}

function sessionCookie(token) {
  const maxAge = SESSION_DAYS * 24 * 3600;
  return `sid=${token}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=${maxAge}`;
}
function clearCookie() {
  return "sid=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0";
}
function getCookie(request, name) {
  const c = request.headers.get("cookie") || "";
  const m = c.match(new RegExp("(?:^|;\\s*)" + name + "=([^;]+)"));
  return m ? m[1] : null;
}

/* ---------------- RUT ---------------- */

// Normaliza: sin puntos/espacios, sin ceros a la izquierda, K mayúscula, con guión.
// Devuelve null si el formato no es válido. (La validez "real" la da la tabla clientes.)
function normalizeRut(input) {
  if (!input) return null;
  let r = String(input).toUpperCase().replace(/[.\s]/g, "").trim();
  if (!r.includes("-") && r.length >= 2) r = r.slice(0, -1) + "-" + r.slice(-1);
  const [numRaw, dv] = r.split("-");
  if (!numRaw || dv === undefined) return null;
  const num = numRaw.replace(/^0+/, "") || "0";
  if (!/^\d{6,8}$/.test(num)) return null;
  if (!/^[0-9K]$/.test(dv)) return null;
  return `${num}-${dv}`;
}

/* ---------------- Hash (PBKDF2 / Web Crypto) ---------------- */

async function hashPassword(password, saltB64) {
  const enc = new TextEncoder();
  const salt = saltB64 ? b64ToBytes(saltB64) : crypto.getRandomValues(new Uint8Array(16));
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt, iterations: PBKDF2_ITER, hash: "SHA-256" }, key, 256);
  return bytesToB64(salt) + ":" + bytesToB64(new Uint8Array(bits));
}

async function verifyPassword(password, stored) {
  const [saltB64, hashB64] = (stored || "").split(":");
  if (!saltB64 || !hashB64) return false;
  const recomputed = await hashPassword(password, saltB64);
  const a = recomputed.split(":")[1];
  return timingSafeEqual(a, hashB64);
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

function bytesToB64(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}
function b64ToBytes(b64) {
  const s = atob(b64);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out;
}

/* ---------------- helpers ---------------- */

async function readJson(request) {
  try { return await request.json(); } catch { return {}; }
}
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { "content-type": "application/json" },
  });
}
