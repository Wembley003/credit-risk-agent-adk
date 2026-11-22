"""Pruebas de las herramientas del agente (no necesitan llave de API).

Cada prueba recalcula las métricas directamente desde el CSV con el módulo
`csv` de la biblioteca estándar, por un camino independiente al de
`credit_risk_agent.tools`, y compara los resultados.
"""

import csv

import pytest

from credit_risk_agent import tools


def _leer_csv():
    with open(tools.DATA_PATH, newline="", encoding="utf-8") as f:
        return [
            {
                "id_credito": fila["id_credito"],
                "segmento": fila["segmento"],
                "ead": float(fila["ead"]),
                "pd": float(fila["pd"]),
                "lgd": float(fila["lgd"]),
                "estatus": fila["estatus"],
            }
            for fila in csv.DictReader(f)
        ]


def test_resumen_cartera():
    cartera = _leer_csv()
    ead = sum(c["ead"] for c in cartera)
    el = sum(c["ead"] * c["pd"] * c["lgd"] for c in cartera)
    vencido = sum(c["ead"] for c in cartera if c["estatus"] == "vencido")
    resumen = tools.resumen_cartera()
    assert resumen["numero_creditos"] == len(cartera) == 24
    assert resumen["ead_total"] == pytest.approx(ead)
    assert resumen["perdida_esperada_total"] == pytest.approx(el)
    assert resumen["pd_ponderada"] == pytest.approx(
        round(sum(c["ead"] * c["pd"] for c in cartera) / ead, 4)
    )
    assert resumen["cartera_vencida"] == pytest.approx(vencido)
    assert resumen["morosidad_pct"] == pytest.approx(round(100 * vencido / ead, 2))
    assert resumen["perdida_esperada_total"] < resumen["ead_total"]


def test_desglose_por_segmento_suma_al_total():
    resumen = tools.resumen_cartera()
    desglose = tools.desglose_por_segmento()
    assert set(desglose) == {"Consumo", "Hipotecario", "PyME", "Tarjeta"}
    assert sum(v["ead_total"] for v in desglose.values()) == pytest.approx(
        resumen["ead_total"]
    )
    assert sum(v["perdida_esperada"] for v in desglose.values()) == pytest.approx(
        resumen["perdida_esperada_total"]
    )
    assert sum(v["numero_creditos"] for v in desglose.values()) == 24


def test_mayores_exposiciones_ordenadas():
    top = tools.mayores_exposiciones(5)["top"]
    assert len(top) == 5
    eads = [c["ead"] for c in top]
    assert eads == sorted(eads, reverse=True)
    assert top[0]["id_credito"] == "P-003"  # la mayor exposición del ejemplo
    assert top[0]["perdida_esperada"] == pytest.approx(
        2_500_000 * 0.06 * 0.45
    )


def test_creditos_vencidos():
    cartera = _leer_csv()
    esperados = [c for c in cartera if c["estatus"] == "vencido"]
    resultado = tools.creditos_vencidos()
    assert resultado["numero_vencidos"] == len(esperados) == 8
    assert resultado["ead_vencida"] == pytest.approx(
        sum(c["ead"] for c in esperados)
    )
    assert resultado["perdida_esperada_vencida"] == pytest.approx(
        sum(c["ead"] * c["pd"] * c["lgd"] for c in esperados)
    )
    assert all(c["ead"] for c in resultado["creditos"])
