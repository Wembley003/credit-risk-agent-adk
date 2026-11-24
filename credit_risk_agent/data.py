"""Capa: Consultas o análisis — la lectura de la cartera de ejemplo.

Este módulo es la única puerta de entrada a los datos: lee el CSV y
devuelve la lista de créditos. Las herramientas (la capa de reglas)
no abren archivos; preguntan aquí. Si mañana la cartera vive en una
base de datos en vez de un CSV, solo este archivo cambia.
"""

from __future__ import annotations

import csv
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "portfolio_sample.csv"


def cargar_cartera() -> list[dict]:
    """Lee el CSV de ejemplo y devuelve la lista de créditos."""
    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    cartera = []
    for fila in filas:
        cartera.append(
            {
                "id_credito": fila["id_credito"],
                "segmento": fila["segmento"],
                "ead": float(fila["ead"]),
                "pd": float(fila["pd"]),
                "lgd": float(fila["lgd"]),
                "estatus": fila["estatus"],
            }
        )
    return cartera


# Alias histórico: antes la carga vivía en tools.py con este nombre.
_cargar_cartera = cargar_cartera
