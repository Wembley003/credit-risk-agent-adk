# Agente de riesgo de crédito con Google ADK y Gemini

Un agente de IA que responde preguntas sobre una cartera de crédito en español:
exposición (EAD), pérdida esperada (EL), probabilidad de incumplimiento (PD)
y morosidad, por segmento. Está construido con el **Agent Development Kit
(ADK)** de Google y **Gemini**, y las cifras las calcula con herramientas de
Python, no con el modelo: el agente nunca inventa números.

## Qué demuestra

- **ADK**: definición del agente (`Agent`), instrucciones y herramientas.
- **Function tools**: 4 herramientas en Python puro (`resumen_cartera`,
  `desglose_por_segmento`, `mayores_exposiciones`, `creditos_vencidos`).
- **Gemini**: el modelo decide qué herramienta usar y redacta la respuesta.
- **Pruebas sin llave**: las herramientas se prueban con `pytest`, sin API.

## Requisitos

- Python 3.10 o superior.
- Una llave gratuita de Google AI Studio (solo para hablar con el agente;
  la demo y las pruebas no la necesitan).

## Instalación

```bash
git clone https://github.com/Wembley003/credit-risk-agent-adk.git
cd credit-risk-agent-adk
python -m venv .venv
source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Llave gratuita de Gemini

1. Entra a [Google AI Studio](https://aistudio.google.com/) con tu cuenta de Google.
2. Crea una llave en **Get API key** (nivel gratuito).
3. Guárdala en un archivo `.env` (hay un ejemplo en `.env.example`):

```bash
cp .env.example .env
# edita .env y pega tu llave en GOOGLE_API_KEY
```

ADK la lee automáticamente. Nunca subas el `.env` a Git (ya está en
`.gitignore`).

## Cómo correr el agente

Interfaz web (recomendada):

```bash
adk web
```

Abre http://localhost:8000, elige `credit_risk_agent` y pregunta, por ejemplo:

- ¿Cuál es la exposición total y la pérdida esperada de la cartera?
- ¿Qué segmento tiene la mayor morosidad?
- ¿Cuáles son los 5 créditos con mayor exposición?
- ¿Cuánto de la cartera vencida es de PyME?

En terminal:

```bash
adk run credit_risk_agent
```

## Demo sin llave

Las herramientas funcionan sin Gemini. Para ver las cifras que el agente
usaría:

```bash
python demo.py
```

## Pruebas

```bash
pip install pytest
pytest
```

Las pruebas recalculan cada métrica directamente desde el CSV, por un camino
independiente al del código del agente.

## Estructura

```text
credit-risk-agent-adk/
├── credit_risk_agent/
│   ├── __init__.py      # expone root_agent (lo que busca ADK)
│   ├── agent.py         # definición del agente: modelo, instrucción, herramientas
│   └── tools.py         # cálculo de métricas (EAD, EL, PD, morosidad)
├── data/
│   └── portfolio_sample.csv   # cartera sintética de ejemplo (24 créditos)
├── tests/
│   └── test_tools.py    # pruebas de las herramientas (sin llave de API)
├── demo.py              # muestra las cifras sin llamar a Gemini
├── requirements.txt
├── .env.example
└── LICENSE
```

## Datos

La cartera de `data/portfolio_sample.csv` es **sintética**, creada solo para
la demostración: 24 créditos en 4 segmentos (Hipotecario, PyME, Consumo,
Tarjeta) con EAD, PD, LGD y estatus (vigente/vencido). Para usar tus propios
datos, reemplaza ese CSV manteniendo las mismas columnas.

## Notas

- El modelo es `gemini-2.0-flash`. Si Google cambia el nombre del modelo,
  actualízalo en `credit_risk_agent/agent.py`.
- La pérdida esperada se calcula como EL = EAD × PD × LGD; la PD ponderada y
  la morosidad se ponderan por exposición (EAD).

## Licencia

MIT. Ver `LICENSE`.
