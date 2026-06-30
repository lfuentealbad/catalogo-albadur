-- Esquema de la base de datos D1 para el login de clientes de Albadur.
-- NO contiene datos personales (esos se cargan aparte y quedan fuera del repo).

-- Clientes válidos, importados desde la lista de Defontana.
-- Es la "lista blanca": solo estos RUT pueden crear cuenta.
CREATE TABLE IF NOT EXISTS clientes (
  rut    TEXT PRIMARY KEY,   -- normalizado: sin puntos, con guión, K mayúscula (ej. 5359657-6)
  nombre TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'Activo'
);

-- Cuentas creadas por los clientes en la web.
CREATE TABLE IF NOT EXISTS cuentas (
  rut           TEXT PRIMARY KEY REFERENCES clientes(rut),
  password_hash TEXT NOT NULL,   -- PBKDF2 (salt:hash en base64)
  email         TEXT,
  creado        TEXT NOT NULL
);

-- Sesiones activas (token en cookie HttpOnly).
CREATE TABLE IF NOT EXISTS sesiones (
  token  TEXT PRIMARY KEY,
  rut    TEXT NOT NULL REFERENCES cuentas(rut),
  expira INTEGER NOT NULL       -- epoch en milisegundos
);

CREATE INDEX IF NOT EXISTS idx_sesiones_rut ON sesiones(rut);
