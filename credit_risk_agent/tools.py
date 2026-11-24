"""
Capa: Reglas de negocio — las cifras de la cartera, calculadas en Python puro. Las herramientas son además la superficie de consulta del agente: por ellas pregunta a la cartera.
Herramientas del agente: cálculo de métricas de cartera de crédito.

Son funciones puras de Python (sin llamadas al modelo), por eso se pueden
probar sin llave de API. El agente las usa a través de ADK: Gemini decide
cuándo llamarlas y redacta la respuesta con sus resultados.
"""

from __future__ import annotations

from .data import DATA_PATH, _cargar_cartera, cargar_cartera

__all__ = [
    "DATA_PATH",
    "_cargar_cartera",
    "cargar_cartera",
    "resumen_cartera",
    "desglose_por_segmento",
    "mayores_exposiciones",
    "creditos_vencidos",
]


def _perdida_esperada(credito: dict) -> float:
    """Pérdida esperada de un crédito: EAD x PD x LGD."""
    return credito["ead"] * credito["pd"] * credito["lgd"]


def resumen_cartera() -> dict:
    """Resumen general de la cartera: exposición, pérdida esperada, PD ponderada y morosidad.

    Returns:
        dict con numero_creditos, ead_total, perdida_esperada_total,
        pd_ponderada, cartera_vencida y morosidad_pct.
    """
    cartera = _cargar_cartera()
    ead_total = sum(c["ead"] for c in cartera)
    el_total = sum(_perdida_esperada(c) for c in cartera)
    vencido = sum(c["ead"] for c in cartera if c["estatus"] == "vencido")
    return {
        "numero_creditos": len(cartera),
        "ead_total": round(ead_total, 2),
        "perdida_esperada_total": round(el_total, 2),
        "pd_ponderada": round(sum(c["ead"] * c["pd"] for c in cartera) / ead_total, 4),
        "cartera_vencida": round(vencido, 2),
        "morosidad_pct": round(100 * vencido / ead_total, 2),
    }


def desglose_por_segmento() -> dict:
    """Métricas por segmento: créditos, EAD, pérdida esperada, PD ponderada y morosidad."""
    cartera = _cargar_cartera()
    segmentos: dict[str, dict] = {}
    for c in cartera:
        s = segmentos.setdefault(
            c["segmento"],
            {"numero_creditos": 0, "ead": 0.0, "el": 0.0, "ead_pd": 0.0, "vencido": 0.0},
        )
        s["numero_creditos"] += 1
        s["ead"] += c["ead"]
        s["el"] += _perdida_esperada(c)
        s["ead_pd"] += c["ead"] * c["pd"]
        if c["estatus"] == "vencido":
            s["vencido"] += c["ead"]
    return {
        seg: {
            "numero_creditos": v["numero_creditos"],
            "ead_total": round(v["ead"], 2),
            "perdida_esperada": round(v["el"], 2),
            "pd_ponderada": round(v["ead_pd"] / v["ead"], 4),
            "morosidad_pct": round(100 * v["vencido"] / v["ead"], 2),
        }
        for seg, v in sorted(segmentos.items())
    }


def mayores_exposiciones(n: int = 5) -> dict:
    """Los n créditos con mayor exposición (EAD), con su PD, LGD y pérdida esperada."""
    cartera = sorted(_cargar_cartera(), key=lambda c: c["ead"], reverse=True)[: max(n, 1)]
    return {
        "top": [
            {
                "id_credito": c["id_credito"],
                "segmento": c["segmento"],
                "ead": round(c["ead"], 2),
                "pd": c["pd"],
                "lgd": c["lgd"],
                "perdida_esperada": round(_perdida_esperada(c), 2),
                "estatus": c["estatus"],
            }
            for c in cartera
        ]
    }


def creditos_vencidos() -> dict:
    """Créditos en estatus vencido, con su exposición y pérdida esperada."""
    vencidos = [c for c in _cargar_cartera() if c["estatus"] == "vencido"]
    return {
        "numero_vencidos": len(vencidos),
        "ead_vencida": round(sum(c["ead"] for c in vencidos), 2),
        "perdida_esperada_vencida": round(sum(_perdida_esperada(c) for c in vencidos), 2),
        "creditos": [
            {
                "id_credito": c["id_credito"],
                "segmento": c["segmento"],
                "ead": round(c["ead"], 2),
                "pd": c["pd"],
                "lgd": c["lgd"],
            }
            for c in sorted(vencidos, key=lambda c: c["ead"], reverse=True)
        ],
    }
