CREATE TABLE IF NOT EXISTS usuarios (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  telegram_id     INTEGER UNIQUE,
  telefono        TEXT UNIQUE,
  consentimiento  INTEGER NOT NULL DEFAULT 0,
  creado          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ultima_ubicacion (
  usuario_id  INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
  lat         REAL NOT NULL,
  lon         REAL NOT NULL,
  fecha       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  en_vivo     INTEGER NOT NULL DEFAULT 0,
  en_vivo_hasta TEXT
);

CREATE TABLE IF NOT EXISTS ubicaciones (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  lat         REAL NOT NULL,
  lon         REAL NOT NULL,
  fuente      INTEGER NOT NULL DEFAULT 1,
  fecha       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ubic_usuario_fecha
  ON ubicaciones (usuario_id, fecha DESC);

CREATE TABLE IF NOT EXISTS resumen_diario (
  usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  dia          TEXT NOT NULL,
  puntos       INTEGER NOT NULL,
  distancia_m  REAL NOT NULL,
  PRIMARY KEY (usuario_id, dia)
);
