"""Demo sin llave de API: ejecuta las herramientas del agente y muestra las cifras.

Para hablar con el agente (con Gemini) sigue el README: consigue una llave
gratuita en Google AI Studio y corre `adk web` o `adk run`.
"""

import json

from credit_risk_agent.tools import (
    creditos_vencidos,
    desglose_por_segmento,
    mayores_exposiciones,
    resumen_cartera,
)


def _mostrar(titulo, datos):
    print(f"\n== {titulo} ==")
    print(json.dumps(datos, indent=2, ensure_ascii=False))


def main():
    _mostrar("Resumen de la cartera", resumen_cartera())
    _mostrar("Desglose por segmento", desglose_por_segmento())
    _mostrar("Mayores exposiciones (top 5)", mayores_exposiciones(5))
    _mostrar("Créditos vencidos", creditos_vencidos())


if __name__ == "__main__":
    main()
