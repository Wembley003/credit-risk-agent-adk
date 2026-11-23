"""Agente de análisis de cartera de crédito con Google ADK y Gemini.

El agente responde preguntas en español sobre la cartera de ejemplo
(`data/portfolio_sample.csv`) usando herramientas de Python para calcular
las cifras. Nunca inventa cifras: todo número viene de las herramientas.
"""

from google.adk.agents import Agent

from .tools import (
    creditos_vencidos,
    desglose_por_segmento,
    mayores_exposiciones,
    resumen_cartera,
)

INSTRUCCION = """Eres un analista de riesgo de crédito. Respondes en español, de forma breve y con cifras.

Reglas:
- Para cualquier cifra de la cartera (exposición, pérdida esperada, PD, morosidad) usa SIEMPRE las herramientas; nunca inventes ni estimes cifras.
- Si una pregunta no se puede responder con las herramientas, dilo y explica qué dato faltaría.
- Explica cada cifra en una frase: qué mide y por qué importa.
- No das recomendaciones de inversión ni asesoría financiera personalizada.
"""

root_agent = Agent(
    name="credit_risk_agent",
    model="gemini-3.6-flash",
    description="Agente que analiza una cartera de crédito: exposición, pérdida esperada, PD y morosidad por segmento.",
    instruction=INSTRUCCION,
    tools=[resumen_cartera, desglose_por_segmento, mayores_exposiciones, creditos_vencidos],
)
