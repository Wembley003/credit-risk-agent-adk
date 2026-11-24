"""
Capa: Consultas o análisis — el snapshot guardado como libro de Excel.
Exportar un snapshot de la cartera a Excel (openpyxl).

Cuatro hojas: el resumen, el desglose por segmento, las mayores
exposiciones y los créditos vencidos. Es el reporte que se le puede
pasar a alguien que no va a correr el agente: abre el archivo y ve la
cartera entera.

Además, dos tablas dinámicas NATIVAS de Excel (no valores pegados):
una resume la exposición y la pérdida esperada por segmento y otra
por estatus del crédito. Son nativas porque Excel las puede filtrar,
desplegar y recalcular al abrir el archivo; una tabla hecha a mano
con valores fijos no puede. Si una hoja de origen no tiene filas de
datos, su pivote se salta sin romper la exportación: mejor un libro
sin ese pivote que ningún libro.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from .persistence import get_snapshot, list_snapshots
from .pivot_table import add_pivot_table

__all__ = ["export_workbook"]


def _agregar_pivote(wb, hoja_origen, titulo_pivote, nombre_pivote,
                    filas, datos):
    """Agrega una tabla dinámica, o la salta si no hay nada que resumir.

    ``add_pivot_table`` levanta ValueError cuando la hoja de origen no
    tiene filas de datos (por ejemplo, un snapshot sin vencidos en el
    top o sin segmentos). Eso no es un error de la exportación: es
    simplemente que no hay nada que agrupar, así que se salta el
    pivote y el libro sale igual con el resto.
    """
    try:
        add_pivot_table(
            wb,
            source_sheet=hoja_origen,
            pivot_sheet_title=titulo_pivote,
            pivot_name=nombre_pivote,
            row_fields=filas,
            data_fields=datos,
        )
    except ValueError:
        pass


def _write_sheet(wb, title, headers, rows):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    for column in ws.columns:
        width = max(len(str(cell.value)) if cell.value is not None else 0
                    for cell in column)
        ws.column_dimensions[column[0].column_letter].width = min(width + 2, 28)
    return ws


def export_workbook(db_path, xlsx_path, snapshot_id=None):
    """Escribe el libro de Excel de un snapshot (el último, si no se dice cuál)."""
    db_path = Path(db_path)
    xlsx_path = Path(xlsx_path)
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    if snapshot_id is None:
        snapshots = list_snapshots(db_path)
        if not snapshots:
            raise ValueError("la base no tiene snapshots guardados")
        snapshot_id = snapshots[0]["id"]
    snapshot = get_snapshot(db_path, snapshot_id)
    if snapshot is None:
        raise ValueError(f"no existe el snapshot {snapshot_id}")

    wb = Workbook()
    wb.remove(wb.active)

    resumen_rows = [
        ["Créditos", snapshot["numero_creditos"]],
        ["EAD total", snapshot["ead_total"]],
        ["Pérdida esperada total", snapshot["perdida_esperada_total"]],
        ["PD ponderada", snapshot["pd_ponderada"]],
        ["Cartera vencida", snapshot["cartera_vencida"]],
        ["Morosidad (%)", snapshot["morosidad_pct"]],
        ["Fecha (UTC)", snapshot["created_at"]],
    ]
    _write_sheet(wb, "Resumen", ["Métrica", "Valor"], resumen_rows)

    segmento_rows = [
        [s["segmento"], s["numero_creditos"], s["ead_total"],
         s["perdida_esperada"], s["pd_ponderada"], s["morosidad_pct"]]
        for s in snapshot["segmentos"]
    ]
    segmento_ws = _write_sheet(
        wb, "Por segmento",
        ["Segmento", "Créditos", "EAD total", "Pérdida esperada",
         "PD ponderada", "Morosidad (%)"],
        segmento_rows,
    )

    top_rows = [
        [t["puesto"], t["id_credito"], t["segmento"], t["ead"], t["pd"],
         t["lgd"], t["perdida_esperada"], t["estatus"]]
        for t in snapshot["top_exposiciones"]
    ]
    top_ws = _write_sheet(
        wb, "Top exposiciones",
        ["Puesto", "Crédito", "Segmento", "EAD", "PD", "LGD",
         "Pérdida esperada", "Estatus"],
        top_rows,
    )

    vencidos_rows = [
        [v["id_credito"], v["segmento"], v["ead"], v["pd"], v["lgd"]]
        for v in snapshot["vencidos"]
    ]
    _write_sheet(
        wb, "Vencidos",
        ["Crédito", "Segmento", "EAD", "PD", "LGD"],
        vencidos_rows,
    )

    # Las dinámicas se construyen sobre las hojas ya escritas: el
    # segmento agrupa cuánto pesa cada negocio en EAD y en pérdida
    # esperada (ahí se ve de un vistazo dónde se concentra el riesgo),
    # y el estatus separa lo vigente de lo vencido dentro del top de
    # exposiciones, contando además cuántos créditos caen en cada lado.
    # El conteo usa la columna EAD con subtotal "count": cuenta filas,
    # no suma dinero, por eso el nombre visible es distinto.
    _agregar_pivote(
        wb, segmento_ws, "Dinámica por segmento", "PivotSegmento",
        filas=["Segmento"],
        datos=[("EAD total", "EAD total", "sum"),
               ("Pérdida esperada", "Pérdida esperada", "sum"),
               ("Créditos", "Créditos", "sum")],
    )
    _agregar_pivote(
        wb, top_ws, "Dinámica por estatus", "PivotEstatus",
        filas=["Estatus"],
        datos=[("EAD", "EAD", "sum"),
               ("Pérdida esperada", "Pérdida esperada", "sum"),
               ("EAD", "Número de créditos", "count")],
    )

    wb.save(xlsx_path)
    return xlsx_path
