"""Pruebas del volcado a Access (.accdb real con Jackcess).

(a) El volcado a texto: ``dump_access.dump`` deja un CSV por tabla más
``schema.txt`` y ``schema.json`` con las tablas y sus filas.
(b) El .accdb real: ``access/build_access.sh`` construye el archivo y
se verifica con mdbtools que las tablas y los conteos coinciden con
los CSV. Si el toolchain no está (sin java o sin mdbtools, o sin poder
descargar los jars), se salta con el motivo: el volcado en texto sigue
siendo el pack de importación.
"""

import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "access"))

from dump_access import dump  # noqa: E402

from credit_risk_agent import persistence  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ACCESS_DIR = REPO / "access"
ACCDB = ACCESS_DIR / "credit-risk-agent-adk.accdb"

# Filas del snapshot de juguete (la cartera sintética de 24 créditos):
# 1 snapshot, 4 segmentos, top 5 y 8 vencidos.
FILAS_ESPERADAS = {
    "snapshots": 1,
    "segmentos": 4,
    "top_exposiciones": 5,
    "vencidos": 8,
}

JARS = ["jackcess-4.0.5.jar", "commons-lang3-3.14.0.jar",
        "commons-logging-1.3.4.jar"]
MAVEN_JAR = ("https://repo1.maven.org/maven2/com/healthmarketscience/"
             "jackcess/jackcess/4.0.5/jackcess-4.0.5.jar")


def _conteo_mdb(accdb, tabla):
    """Filas de una tabla del .accdb según mdb-export (sin encabezado)."""
    out = subprocess.run(
        ["mdb-export", str(accdb), tabla],
        capture_output=True, text=True, check=True,
    )
    lineas = [ln for ln in out.stdout.splitlines() if ln.strip()]
    return len(lineas) - 1  # la primera línea es el encabezado


def test_dump_produce_csvs_y_schema_con_tablas_y_filas(tmp_path):
    db = tmp_path / "snapshots.db"
    persistence.store_snapshot(db)
    out_dir = tmp_path / "access"
    resumen = dump(db, out_dir)
    assert {t["name"] for t in resumen["tables"]} == set(FILAS_ESPERADAS)
    for tabla in resumen["tables"]:
        assert tabla["rows"] == FILAS_ESPERADAS[tabla["name"]]
        csv_path = out_dir / "csv" / f"{tabla['name']}.csv"
        assert csv_path.exists()
        # Encabezado + una línea por fila.
        lineas = csv_path.read_text(encoding="utf-8").splitlines()
        assert len(lineas) == FILAS_ESPERADAS[tabla["name"]] + 1
    schema_txt = (out_dir / "schema.txt").read_text(encoding="utf-8")
    for nombre in FILAS_ESPERADAS:
        assert f"TABLE|{nombre}" in schema_txt
    schema_json = json.loads(
        (out_dir / "schema.json").read_text(encoding="utf-8")
    )
    assert {t["name"]: t["rows"] for t in schema_json["tables"]} == (
        FILAS_ESPERADAS
    )


def test_accdb_del_repo_existe_y_tiene_las_tablas():
    if not ACCDB.exists():
        pytest.skip("no está generado access/credit-risk-agent-adk.accdb")
    if shutil.which("mdb-tables") is None:
        pytest.skip("mdbtools no está instalado")
    out = subprocess.run(
        ["mdb-tables", "-1", str(ACCDB)],
        capture_output=True, text=True, check=True,
    )
    tablas = {ln.strip() for ln in out.stdout.splitlines() if ln.strip()}
    assert set(FILAS_ESPERADAS) <= tablas
    for nombre, filas in FILAS_ESPERADAS.items():
        assert _conteo_mdb(ACCDB, nombre) == filas


def test_build_access_construye_accdb_verificado_con_mdbtools(tmp_path):
    if shutil.which("java") is None or shutil.which("javac") is None:
        pytest.skip("falta el JDK (java/javac)")
    if shutil.which("mdb-export") is None:
        pytest.skip("mdbtools no está instalado")
    # Copia de trabajo del directorio access (sin los compilados).
    trabajo = tmp_path / "access"
    shutil.copytree(
        ACCESS_DIR, trabajo,
        ignore=shutil.ignore_patterns("build", "*.accdb"),
    )
    lib = trabajo / "lib"
    jars_presentes = lib.exists() and all(
        (lib / jar).exists() for jar in JARS
    )
    if not jars_presentes:
        try:
            req = urllib.request.Request(MAVEN_JAR, method="HEAD")
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pytest.skip("no se pueden descargar los jars de Jackcess")
    db = tmp_path / "snapshots.db"
    persistence.store_snapshot(db)
    resultado = subprocess.run(
        ["bash", str(trabajo / "build_access.sh"), str(db),
         "prueba.accdb"],
        capture_output=True, text=True, timeout=300,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    accdb = trabajo / "prueba.accdb"
    assert accdb.exists()
    for nombre, filas in FILAS_ESPERADAS.items():
        assert _conteo_mdb(accdb, nombre) == filas
