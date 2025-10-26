-- =========================================================
-- TIPOS
-- =========================================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rol_usuario') THEN
    CREATE TYPE rol_usuario AS ENUM ('admin', 'gestor', 'usuario');
  END IF;
END$$;

-- =========================================================
-- TABLAS BÁSICAS
-- =========================================================

-- Escuelas
CREATE TABLE IF NOT EXISTS public.escuelas (
  id       SERIAL PRIMARY KEY,
  nombre   VARCHAR NOT NULL
);

-- Categorías
CREATE TABLE IF NOT EXISTS public.categorias (
  id       SERIAL PRIMARY KEY,
  nombre   VARCHAR NOT NULL
);

-- Edificios
CREATE TABLE IF NOT EXISTS public.edificios (
  id       SERIAL PRIMARY KEY,
  edificio VARCHAR NOT NULL
);

-- Usuarios
CREATE TABLE IF NOT EXISTS public.usuarios (
  id            SERIAL PRIMARY KEY,
  codigo        INTEGER,              -- si debe ser único, descomenta la UNIQUE
  nombre        VARCHAR NOT NULL,
  email         VARCHAR NOT NULL,
  password_hash TEXT    NOT NULL,
  rol           rol_usuario NOT NULL,
  escuela_id    INTEGER REFERENCES public.escuelas(id) ON UPDATE CASCADE ON DELETE SET NULL,
  activo        BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (email)
  -- ,UNIQUE (codigo)
);

-- Salones (habitaciones/aulas)
CREATE TABLE IF NOT EXISTS public.salones (
  id          SERIAL PRIMARY KEY,
  salon       JSONB,  -- datos del salón (número, capacidad, etc.)
  id_edificio INTEGER REFERENCES public.edificios(id) ON UPDATE CASCADE ON DELETE SET NULL
);

-- =========================================================
-- INVENTARIO
-- =========================================================

-- Items del inventario
CREATE TABLE IF NOT EXISTS public.inventario_items (
  id               SERIAL PRIMARY KEY,
  inventario       VARCHAR NOT NULL,        -- código o folio de inventario
  descripcion      TEXT,
  marca            VARCHAR,
  valor            NUMERIC,
  fecha_recibido   DATE,
  categoria_id     INTEGER REFERENCES public.categorias(id) ON UPDATE CASCADE ON DELETE SET NULL,
  ubicacion_id     INTEGER REFERENCES public.salones(id)   ON UPDATE CASCADE ON DELETE SET NULL,
  entregado_por_id INTEGER REFERENCES public.usuarios(id)  ON UPDATE CASCADE ON DELETE SET NULL,
  recibido_por_id  INTEGER REFERENCES public.usuarios(id)  ON UPDATE CASCADE ON DELETE SET NULL,
  escuela_id       INTEGER REFERENCES public.escuelas(id)  ON UPDATE CASCADE ON DELETE SET NULL
);

-- Trazabilidad / historial de movimientos del inventario
CREATE TABLE IF NOT EXISTS public.inventario_trazabilidad (
  id            BIGSERIAL PRIMARY KEY,
  inventario_id INTEGER NOT NULL REFERENCES public.inventario_items(id)
                ON UPDATE CASCADE ON DELETE CASCADE,
  fecha         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  accion        TEXT,     -- p.ej. "alta", "traslado", "baja", etc.
  detalle       TEXT,
  usuario_id    INTEGER REFERENCES public.usuarios(id) ON UPDATE CASCADE ON DELETE SET NULL,
  meta          JSONB
);

-- =========================================================
-- (Opcional) Tablas de Django que aparecen en el diagrama
-- =========================================================

CREATE TABLE IF NOT EXISTS public.django_migrations (
  id      BIGSERIAL PRIMARY KEY,
  app     VARCHAR NOT NULL,
  name    VARCHAR NOT NULL,
  applied TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS public.django_session (
  session_key VARCHAR PRIMARY KEY,
  session_data TEXT NOT NULL,
  expire_date TIMESTAMPTZ NOT NULL
);

-- =========================================================
-- ÍNDICES ÚTILES
-- =========================================================
CREATE INDEX IF NOT EXISTS idx_inventario_items_inventario
  ON public.inventario_items (inventario);

CREATE INDEX IF NOT EXISTS idx_inventario_items_categoria
  ON public.inventario_items (categoria_id);

CREATE INDEX IF NOT EXISTS idx_inventario_items_ubicacion
  ON public.inventario_items (ubicacion_id);

CREATE INDEX IF NOT EXISTS idx_inventario_trazabilidad_inventario_fecha
  ON public.inventario_trazabilidad (inventario_id, fecha);

CREATE INDEX IF NOT EXISTS idx_usuarios_escuela
  ON public.usuarios (escuela_id);

CREATE INDEX IF NOT EXISTS idx_salones_edificio
  ON public.salones (id_edificio);
