"""
Capa: Consultas o análisis — los snapshots guardados para consultarlos después.
Guardar snapshots de la cartera en SQLite.

El agente calcula las métricas cada vez que se le pregunta, pero no
guarda nada: si mañana cambia el CSV, el número de hoy se pierde y no
hay forma de comparar. Este módulo es la memoria del agente: cada vez
que se guarda un snapshot quedan el resumen, el desglose por segmento,
las mayores exposiciones y los créditos vencidos, con fecha. Así se
puede ver cómo se mueve la cartera en el tiempo sin volver a correr
nada.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import tools

__all__ = [
    "init_db",
    "store_snapshot",
    "list_snapshots",
    "get_snapshot",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at              TEXT NOT NULL,
    numero_creditos         INTEGER NOT NULL,
    ead_total               REAL NOT NULL,
    perdida_esperada_total  REAL NOT NULL,
    pd_ponderada            REAL NOT NULL,
    cartera_vencida         REAL NOT NULL,
    morosidad_pct           REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS segmentos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id      INTEGER NOT NULL REFERENCES snapshots (id),
    segmento         TEXT NOT NULL,
    numero_creditos  INTEGER NOT NULL,
    ead_total        REAL NOT NULL,
    perdida_esperada REAL NOT NULL,
    pd_ponderada     REAL NOT NULL,
    morosidad_pct    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS top_exposiciones (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id       INTEGER NOT NULL REFERENCES snapshots (id),
    puesto            INTEGER NOT NULL,
    id_credito        TEXT NOT NULL,
    segmento          TEXT NOT NULL,
    ead               REAL NOT NULL,
    pd                REAL NOT NULL,
    lgd               REAL NOT NULL,
    perdida_esperada  REAL NOT NULL,
    estatus           TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vencidos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id  INTEGER NOT NULL REFERENCES snapshots (id),
    id_credito   TEXT NOT NULL,
    segmento     TEXT NOT NULL,
    ead          REAL NOT NULL,
    pd           REAL NOT NULL,
    lgd          REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_segmentos_snap ON segmentos (snapshot_id);
CREATE INDEX IF NOT EXISTS idx_top_snap ON top_exposiciones (snapshot_id);
CREATE INDEX IF NOT EXISTS idx_vencidos_snap ON vencidos (snapshot_id);
"""


def _connect(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path):
    """Crea las tablas si no existen."""
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)


def store_snapshot(db_path):
    """Calcula las métricas con las herramientas del agente y las guarda.

    Devuelve el id del snapshot. Las cifras salen de ``tools`` — las
    mismas funciones que usa el agente para responder — así que lo
    guardado es exactamente lo que el agente diría si le preguntaran.
    """
    init_db(db_path)
    resumen = tools.resumen_cartera()
    desglose = tools.desglose_por_segmento()
    top = tools.mayores_exposiciones(5)["top"]
    vencidos = tools.creditos_vencidos()
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO snapshots
               (created_at, numero_creditos, ead_total,
                perdida_esperada_total, pd_ponderada, cartera_vencida,
                morosidad_pct) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (created_at, resumen["numero_creditos"], resumen["ead_total"],
             resumen["perdida_esperada_total"], resumen["pd_ponderada"],
             resumen["cartera_vencida"], resumen["morosidad_pct"]),
        )
        snapshot_id = cur.lastrowid
        for segmento, m in desglose.items():
            conn.execute(
                """INSERT INTO segmentos
                   (snapshot_id, segmento, numero_creditos, ead_total,
                    perdida_esperada, pd_ponderada, morosidad_pct)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (snapshot_id, segmento, m["numero_creditos"],
                 m["ead_total"], m["perdida_esperada"], m["pd_ponderada"],
                 m["morosidad_pct"]),
            )
        for puesto, credito in enumerate(top, start=1):
            conn.execute(
                """INSERT INTO top_exposiciones
                   (snapshot_id, puesto, id_credito, segmento, ead, pd,
                    lgd, perdida_esperada, estatus)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (snapshot_id, puesto, credito["id_credito"],
                 credito["segmento"], credito["ead"], credito["pd"],
                 credito["lgd"], credito["perdida_esperada"],
                 credito["estatus"]),
            )
        for credito in vencidos["creditos"]:
            conn.execute(
                """INSERT INTO vencidos
                   (snapshot_id, id_credito, segmento, ead, pd, lgd)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (snapshot_id, credito["id_credito"], credito["segmento"],
                 credito["ead"], credito["pd"], credito["lgd"]),
            )
    return snapshot_id


def list_snapshots(db_path):
    """Todos los snapshots guardados, del más reciente al más viejo."""
    init_db(db_path)
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM snapshots ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_snapshot(db_path, snapshot_id):
    """Un snapshot con su desglose, su top y sus vencidos."""
    init_db(db_path)
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)
        ).fetchone()
        if row is None:
            return None
        snapshot = dict(row)
        snapshot["segmentos"] = [
            dict(s) for s in conn.execute(
                "SELECT segmento, numero_creditos, ead_total,"
                " perdida_esperada, pd_ponderada, morosidad_pct"
                " FROM segmentos WHERE snapshot_id = ? ORDER BY segmento",
                (snapshot_id,),
            ).fetchall()
        ]
        snapshot["top_exposiciones"] = [
            dict(t) for t in conn.execute(
                "SELECT puesto, id_credito, segmento, ead, pd, lgd,"
                " perdida_esperada, estatus FROM top_exposiciones"
                " WHERE snapshot_id = ? ORDER BY puesto",
                (snapshot_id,),
            ).fetchall()
        ]
        snapshot["vencidos"] = [
            dict(v) for v in conn.execute(
                "SELECT id_credito, segmento, ead, pd, lgd FROM vencidos"
                " WHERE snapshot_id = ? ORDER BY ead DESC",
                (snapshot_id,),
            ).fetchall()
        ]
    return snapshot
