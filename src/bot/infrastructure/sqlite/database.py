import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"
SCHEMA_PATH = Path(
    os.environ.get("SCHEMA_PATH", Path(__file__).with_name("schema.sql"))
)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def ahora_utc() -> str:
    return datetime.now(timezone.utc).strftime(FORMATO_FECHA)


def debe_guardar(
    ultima,
    lat: float,
    lon: float,
    fecha: str,
    min_metros: float = 30,
    max_segundos: int = 600,
) -> bool:
    if ultima is None:
        return True
    if haversine_m(ultima["lat"], ultima["lon"], lat, lon) >= min_metros:
        return True
    segundos = (
        datetime.strptime(fecha, FORMATO_FECHA)
        - datetime.strptime(ultima["fecha"], FORMATO_FECHA)
    ).total_seconds()
    return segundos >= max_segundos


def normalizar_dia(dia: date | str | None) -> str:
    if dia is None:
        dia = date.today() - timedelta(days=1)
    return dia.isoformat()[:10] if hasattr(dia, "isoformat") else str(dia)[:10]


def calcular_resumen(puntos) -> dict[int, dict]:
    acumulado: dict[int, dict] = {}
    for fila in puntos:
        uid = fila["usuario_id"]
        actual = acumulado.get(uid)
        if actual is None:
            acumulado[uid] = {
                "puntos": 1,
                "distancia_m": 0.0,
                "lat": fila["lat"],
                "lon": fila["lon"],
            }
            continue
        actual["distancia_m"] += haversine_m(
            actual["lat"], actual["lon"], fila["lat"], fila["lon"]
        )
        actual["puntos"] += 1
        actual["lat"], actual["lon"] = fila["lat"], fila["lon"]
    return acumulado


# Columnas agregadas después de la primera versión del esquema.
# ``CREATE TABLE IF NOT EXISTS`` no las añade a una BD que ya existía.
_COLUMNAS_NUEVAS = {
    "ultima_ubicacion": {
        "en_vivo": "INTEGER NOT NULL DEFAULT 0",
        "en_vivo_hasta": "TEXT",
    },
}


def _migrar(con: sqlite3.Connection) -> None:
    for tabla, columnas in _COLUMNAS_NUEVAS.items():
        existentes = {fila[1] for fila in con.execute(f"PRAGMA table_info({tabla})")}
        for nombre, definicion in columnas.items():
            if nombre not in existentes:
                con.execute(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {definicion}")


def crear_bd(db_path: str, schema_path: Path = SCHEMA_PATH) -> str:
    con = sqlite3.connect(db_path)
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(Path(schema_path).read_text(encoding="utf-8"))
        _migrar(con)
        con.commit()
    finally:
        con.close()
    return db_path


class SQLiteDatabase:
    def __init__(
        self,
        db_path: str = "bot.db",
        min_metros: float = 30,
        max_segundos: int = 600,
    ) -> None:
        self.db_path = db_path
        self.min_metros = min_metros
        self.max_segundos = max_segundos
        crear_bd(db_path)

    @contextmanager
    def _con(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def obtener_usuarios(self) -> list[sqlite3.Row]:
        with self._con() as con:
            return con.execute("SELECT * FROM usuarios").fetchall()

    def crear_usuario(
        self, telegram_id: int | None = None, telefono: str | None = None
    ) -> int:
        if telegram_id is None and telefono is None:
            raise ValueError("Se requiere telegram_id o telefono")
        with self._con() as con:
            if telegram_id is not None:
                fila = con.execute(
                    "SELECT id FROM usuarios WHERE telegram_id = ?", (telegram_id,)
                ).fetchone()
            else:
                fila = con.execute(
                    "SELECT id FROM usuarios WHERE telefono = ?", (telefono,)
                ).fetchone()
            if fila is not None:
                return fila["id"]
            cur = con.execute(
                "INSERT INTO usuarios (telegram_id, telefono) VALUES (?, ?)",
                (telegram_id, telefono),
            )
            return cur.lastrowid

    def obtener_usuario(self, usuario_id: int) -> sqlite3.Row | None:
        with self._con() as con:
            return con.execute(
                "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
            ).fetchone()

    def obtener_usuario_por_telegram(self, telegram_id: int) -> sqlite3.Row | None:
        if telegram_id is None:
            return None
        with self._con() as con:
            return con.execute(
                "SELECT * FROM usuarios WHERE telegram_id = ?", (telegram_id,)
            ).fetchone()

    def borrar_usuario(self, usuario_id: int) -> bool:
        with self._con() as con:
            cur = con.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
            return cur.rowcount > 0

    def guardar_datos_personales(
        self,
        usuario_id: int,
        telefono: str | None = None,
        consentimiento: bool | None = None,
    ) -> bool:
        campos: list[str] = []
        valores: list = []
        if telefono is not None:
            campos.append("telefono = ?")
            valores.append(telefono)
        if consentimiento is not None:
            campos.append("consentimiento = ?")
            valores.append(1 if consentimiento else 0)
        if not campos:
            return False
        valores.append(usuario_id)
        with self._con() as con:
            try:
                cur = con.execute(
                    f"UPDATE usuarios SET {', '.join(campos)} WHERE id = ?", valores
                )
            except sqlite3.IntegrityError:
                return False
            return cur.rowcount > 0

    def guardar_ubicacion(
        self,
        usuario_id: int,
        lat: float,
        lon: float,
        fuente: int = 1,
        fecha: str | None = None,
        en_vivo: bool = False,
        en_vivo_hasta: str | None = None,
    ) -> bool:
        fecha = fecha or ahora_utc()
        with self._con() as con:
            ultima = con.execute(
                "SELECT lat, lon, fecha FROM ultima_ubicacion WHERE usuario_id = ?",
                (usuario_id,),
            ).fetchone()
            insertar = debe_guardar(
                ultima, lat, lon, fecha, self.min_metros, self.max_segundos
            )
            con.execute(
                """
                INSERT INTO ultima_ubicacion
                  (usuario_id, lat, lon, fecha, en_vivo, en_vivo_hasta)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(usuario_id) DO UPDATE SET
                  lat = excluded.lat, lon = excluded.lon, fecha = excluded.fecha,
                  en_vivo = excluded.en_vivo, en_vivo_hasta = excluded.en_vivo_hasta
                """,
                (usuario_id, lat, lon, fecha, 1 if en_vivo else 0, en_vivo_hasta),
            )
            if insertar:
                con.execute(
                    "INSERT INTO ubicaciones (usuario_id, lat, lon, fuente, fecha) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (usuario_id, lat, lon, fuente, fecha),
                )
            return insertar

    def obtener_ultima(self, usuario_id: int) -> sqlite3.Row | None:
        with self._con() as con:
            return con.execute(
                "SELECT * FROM ultima_ubicacion WHERE usuario_id = ?", (usuario_id,)
            ).fetchone()

    def terminar_en_vivo(self, usuario_id: int) -> bool:
        with self._con() as con:
            cur = con.execute(
                "UPDATE ultima_ubicacion SET en_vivo = 0, en_vivo_hasta = NULL "
                "WHERE usuario_id = ?",
                (usuario_id,),
            )
            return cur.rowcount > 0

    def resumir_ultimo_dia(self, dia: date | str | None = None) -> int:
        dia = normalizar_dia(dia)
        return self.guardar_resumen(dia, calcular_resumen(self._puntos_del_dia(dia)))

    def _puntos_del_dia(self, dia: str) -> list[sqlite3.Row]:
        with self._con() as con:
            return con.execute(
                """
                SELECT usuario_id, lat, lon FROM ubicaciones
                WHERE substr(fecha, 1, 10) = ?
                ORDER BY usuario_id, fecha
                """,
                (dia,),
            ).fetchall()

    def guardar_resumen(self, dia: str, resumen: dict[int, dict]) -> int:
        with self._con() as con:
            for uid, datos in resumen.items():
                con.execute(
                    """
                    INSERT INTO resumen_diario (usuario_id, dia, puntos, distancia_m)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(usuario_id, dia) DO UPDATE SET
                      puntos = excluded.puntos, distancia_m = excluded.distancia_m
                    """,
                    (uid, dia, datos["puntos"], datos["distancia_m"]),
                )
            return len(resumen)
