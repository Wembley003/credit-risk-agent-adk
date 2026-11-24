"""Pruebas de la exportación a Excel."""

import sqlite3
import zipfile

import pytest
from openpyxl import load_workbook

from credit_risk_agent import excel_export, persistence


# Las piezas que una tabla dinámica NATIVA deja dentro del zip: su
# definición, su caché (qué columnas hay) y sus registros (las filas).
# Si falta una, Excel abre el archivo y dice que está dañado, así que
# se comprueban las seis, dos por cada pivote.
PARTES_PIVOTE = [
    "xl/pivotTables/pivotTable1.xml",
    "xl/pivotTables/pivotTable2.xml",
    "xl/pivotCache/pivotCacheDefinition1.xml",
    "xl/pivotCache/pivotCacheDefinition2.xml",
    "xl/pivotCache/pivotCacheRecords1.xml",
    "xl/pivotCache/pivotCacheRecords2.xml",
]


def test_export_crea_cuatro_hojas_con_datos(tmp_path):
    db = tmp_path / "snapshots.db"
    xlsx = tmp_path / "cartera.xlsx"
    persistence.store_snapshot(db)
    out = excel_export.export_workbook(db, xlsx)
    assert out == xlsx
    wb = load_workbook(xlsx)
    assert wb.sheetnames == [
        "Resumen", "Por segmento", "Top exposiciones", "Vencidos",
        "Dinámica por segmento", "Dinámica por estatus",
    ]
    resumen = wb["Resumen"]
    valores = {
        resumen.cell(row=r, column=1).value: resumen.cell(row=r, column=2).value
        for r in range(2, resumen.max_row + 1)
    }
    assert valores["EAD total"] == pytest.approx(17_955_000.0)
    assert valores["Pérdida esperada total"] == pytest.approx(358_595.0)
    assert valores["Créditos"] == 24
    assert wb["Por segmento"].max_row == 5  # encabezado + 4 segmentos
    assert wb["Top exposiciones"].max_row == 6  # encabezado + 5 créditos
    assert wb["Vencidos"].max_row == 9  # encabezado + 8 vencidos
    top = wb["Top exposiciones"]
    assert top["B2"].value == "P-003"


def test_export_sin_snapshots_falla_claro(tmp_path):
    db = tmp_path / "vacia.db"
    persistence.init_db(db)
    with pytest.raises(ValueError, match="no tiene snapshots"):
        excel_export.export_workbook(db, tmp_path / "vacia.xlsx")


def test_export_incluye_tablas_dinamicas_nativas(tmp_path):
    db = tmp_path / "snapshots.db"
    xlsx = tmp_path / "cartera.xlsx"
    persistence.store_snapshot(db)
    excel_export.export_workbook(db, xlsx)
    with zipfile.ZipFile(xlsx) as zf:
        nombres = zf.namelist()
    for parte in PARTES_PIVOTE:
        assert parte in nombres, f"falta {parte} en el .xlsx"
    wb = load_workbook(xlsx)
    assert "Dinámica por segmento" in wb.sheetnames
    assert "Dinámica por estatus" in wb.sheetnames
    # openpyxl relee las definiciones: cada hoja de pivote trae la suya,
    # con su nombre y su caché, no una hoja con valores pegados.
    pivotes_segmento = wb["Dinámica por segmento"]._pivots
    assert [p.name for p in pivotes_segmento] == ["PivotSegmento"]
    pivotes_estatus = wb["Dinámica por estatus"]._pivots
    assert [p.name for p in pivotes_estatus] == ["PivotEstatus"]
    assert pivotes_segmento[0].cacheId != pivotes_estatus[0].cacheId


def test_export_sin_filas_salta_los_pivotes_sin_romper(tmp_path):
    # Un snapshot con resumen pero sin segmentos ni top: no hay nada
    # que agrupar, así que los pivotes se saltan y el libro sale igual
    # con las cuatro hojas base (solo encabezados en las vacías).
    db = tmp_path / "sin_filas.db"
    persistence.init_db(db)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO snapshots (created_at, numero_creditos,"
            " ead_total, perdida_esperada_total, pd_ponderada,"
            " cartera_vencida, morosidad_pct)"
            " VALUES ('2026-11-24T00:00:00+00:00', 0, 0, 0, 0, 0, 0)"
        )
    xlsx = tmp_path / "sin_filas.xlsx"
    excel_export.export_workbook(db, xlsx)
    wb = load_workbook(xlsx)
    assert wb.sheetnames == [
        "Resumen", "Por segmento", "Top exposiciones", "Vencidos",
    ]
    with zipfile.ZipFile(xlsx) as zf:
        nombres = zf.namelist()
    for parte in PARTES_PIVOTE:
        assert parte not in nombres
