-- =============================
-- Tipos (roles)
-- =============================
CREATE TYPE rol_usuario AS ENUM ('director','profesor');

-- =============================
-- Tablas maestras
-- =============================
CREATE TABLE escuelas (
  id         SERIAL PRIMARY KEY,
  nombre     VARCHAR(150) UNIQUE NOT NULL
);

CREATE TABLE usuarios (
  id            SERIAL PRIMARY KEY,
  codigo        VARCHAR(50) UNIQUE NOT NULL,
  nombre        VARCHAR(150) NOT NULL,
  email         VARCHAR(150) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  rol           rol_usuario NOT NULL DEFAULT 'profesor',
  escuela_id    INT REFERENCES escuelas(id) ON DELETE RESTRICT,
  activo        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE categorias (
  id     SERIAL PRIMARY KEY,
  nombre VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE ubicaciones (
  id       SERIAL PRIMARY KEY,
  edificio VARCHAR(120) NOT NULL,
  salon    VARCHAR(120) NOT NULL,
  UNIQUE(edificio, salon)
);

-- =============================
-- Inventario
-- =============================
CREATE TABLE inventario_items (
  id               SERIAL PRIMARY KEY,
  inventario       VARCHAR(200) NOT NULL,   -- nombre del bien
  descripcion      TEXT,
  marca            VARCHAR(120),
  valor            NUMERIC(12,2) NOT NULL DEFAULT 0,
  fecha_recibido   DATE NOT NULL,
  categoria_id     INT REFERENCES categorias(id) ON DELETE SET NULL,
  ubicacion_id     INT REFERENCES ubicaciones(id) ON DELETE SET NULL,
  entregado_por_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
  recibido_por_id  INT REFERENCES usuarios(id) ON DELETE SET NULL,
  escuela_id       INT REFERENCES escuelas(id) ON DELETE SET NULL
);
-- Enum solo si no existe
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'accion_traza') THEN
    CREATE TYPE accion_traza AS ENUM ('CREAR','ELIMINAR','TRASPASAR');
  END IF;
END$$;

CREATE TABLE IF NOT EXISTS inventario_trazabilidad (
  id          BIGSERIAL PRIMARY KEY,
  inventario  VARCHAR NOT NULL
              REFERENCES inventario_items(inventario) ON DELETE CASCADE,
  fecha       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  accion      TEXT NOT NULL,      -- la defines tú desde el back: 'CREAR', 'ELIMINAR', 'TRASPASAR', etc.
  detalle     TEXT,               -- opcional
  usuario_id  INT4 REFERENCES usuarios(id),
  meta        JSONB               -- para datos extra; p.ej. en traslado: {"ubicacion_anterior": 3, "ubicacion_nueva": 7}
);

-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_traza_inv_fecha ON inventario_trazabilidad(inventario, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_traza_accion    ON inventario_trazabilidad(accion);
CREATE INDEX IF NOT EXISTS idx_traza_meta_gin  ON inventario_trazabilidad USING GIN (meta);

