# Diseño Fase 2 — Cuentas de cliente + integración Defontana

Documento de diseño para la evolución del catálogo Albadur. Define la
arquitectura, el modelo de datos, el flujo de autenticación y el plan por etapas.

> **Estado:** aprobado en lo conceptual (2026-06-28). Bloqueado para
> implementación completa hasta tener **acceso a la API de Defontana** y una
> **cuenta de Cloudflare**.

---

## 1. Objetivo

Sobre el catálogo público actual (sin precios), agregar:

1. **Sección "Más vendidos"** — ranking de productos, primero curado a mano y
   luego alimentado automáticamente desde las ventas de Defontana.
2. **Cuentas de cliente** con login, para que el cliente pueda:
   - Ver su **historial de compras** y **recomprar** rápido.
   - Quedar **identificado** automáticamente al enviar un pedido.
   - Ver sus **"más vendidos" personalizados** (según su propio historial).

El catálogo **sigue siendo público** (no se restringe a clientes). El login es
opcional y aditivo.

## 2. Decisiones tomadas

| Tema | Decisión |
|------|----------|
| Precios en la web | **No** se muestran. |
| Más vendidos | Ranking general + personalizado por cliente. |
| Login | **RUT validado contra Defontana + contraseña.** Solo clientes reales pueden registrarse. |
| Rol de Defontana | Solo lectura: validar clientes, traer historial y calcular más vendidos. |
| Infraestructura | Cloudflare (Pages + Workers + D1). |

## 3. Arquitectura

```
Navegador (catálogo)  ──►  Cloudflare Pages   (sitio estático: el catálogo actual)
        │
        ├─ login / mi cuenta ──►  Cloudflare Worker (API)  ──►  D1 (cuentas)
        │                                  │
        │                                  └──►  API Defontana (JWT)
        │                                          · validar RUT (clientes)
        │                                          · historial de ventas
        └─ "más vendidos" ◄── destacados.json / KV  ◄── Worker programado (cron)
                                                            └─ agrega ventas → ranking
```

- **Cloudflare Pages**: hospeda el catálogo. Se conecta al repo de GitHub →
  despliegue automático en cada push.
- **Cloudflare Worker (API)**: backend con la lógica sensible. Guarda las
  credenciales de Defontana como *secrets* (nunca llegan al navegador).
- **Cloudflare D1** (SQLite serverless): cuentas de cliente.
- **Worker programado (Cron Trigger)**: una vez al día baja las ventas recientes
  de Defontana, calcula el ranking de más vendidos y lo publica.

### ¿Por qué backend?
Validar RUT, guardar contraseñas y llamar a Defontana **no se puede hacer desde
el navegador** sin exponer credenciales. El Worker es esa capa segura.

## 4. Modelo de datos (D1)

```sql
CREATE TABLE clientes (
  rut           TEXT PRIMARY KEY,      -- normalizado sin puntos, con guión
  defontana_id  TEXT,                  -- id del cliente en Defontana
  nombre        TEXT,
  email         TEXT,
  password_hash TEXT NOT NULL,         -- hash (bcrypt/scrypt), nunca texto plano
  creado        TEXT NOT NULL
);

CREATE TABLE sesiones (
  token    TEXT PRIMARY KEY,
  rut      TEXT NOT NULL REFERENCES clientes(rut),
  expira   TEXT NOT NULL
);
```

El **historial de compras** y los **más vendidos** NO se guardan: se leen de
Defontana en vivo (con caché corto) para no duplicar datos sensibles.

## 5. Flujo de autenticación

**Registro:**
1. Cliente ingresa su RUT.
2. Worker valida contra el módulo de clientes de Defontana.
   - Si no existe → "No encontramos tu RUT como cliente. Contáctanos."
   - Si existe → pide crear contraseña.
3. Se guarda en D1 (`rut`, `defontana_id`, hash de contraseña).

**Login:** RUT + contraseña → Worker verifica hash → entrega token de sesión.

**Seguridad:** contraseñas con hash fuerte; tokens de sesión con expiración;
rate-limiting en login; HTTPS (lo da Cloudflare).

## 6. Privacidad (Chile · Ley 21.719)

- Aviso de privacidad simple: qué datos se guardan (RUT, nombre, correo) y para
  qué.
- Solo se almacena lo mínimo. Contraseñas siempre con hash.
- Botón para eliminar la cuenta.

## 7. Plan por etapas

| Etapa | Qué | Depende de |
|-------|-----|------------|
| **0 — hecho** | Catálogo público + PDF + repo + Pages | — |
| **1 — ahora** | Sección **"Más vendidos"** con lista curada a mano (`destacados.json`) | nada |
| **2** | Migrar hosting a **Cloudflare Pages** | cuenta Cloudflare |
| **3** | **Worker + D1**: registro/login con RUT validado contra Defontana | API Defontana + Cloudflare |
| **4** | **Historial + recompra** e identificación automática en el pedido | etapa 3 |
| **5** | **Más vendidos automáticos** (cron) + personalizados por cliente | etapa 3 |

## 8. Lo que se necesita del negocio

1. **Defontana** — contactar a *Post-Venta* y solicitar:
   - Activación del acceso **API REST**.
   - Acceso a los módulos **Sale** (ventas y clientes) e **Inventory**.
   - Credenciales de un **usuario de API**.
2. **Cloudflare** — crear una cuenta (gratuita) para Pages/Workers/D1.

Las credenciales se entregan de forma segura (no en texto plano por chat) y se
cargan como *secrets* en Cloudflare.
