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
independiente al del código del agente. **21 pruebas, todas en verde**,
incluidas las de capas (`tests/test_layers.py`): verifican que el
agente solo usa las cuatro herramientas, que las reglas dan las cifras
conocidas y que las capas no se mezclan (las reglas corren con openpyxl
y sqlite3 bloqueados).

```bash
./run_tests.sh   # lo mismo, buscando el venv solo
```

## Guardar snapshots: SQLite + Excel (nuevo)

El agente calcula las métricas cada vez que se le pregunta, pero no
guarda nada: si mañana cambia el CSV, el número de hoy se pierde.
Ahora cada snapshot queda guardado en SQLite (`persistence.py`) con
el resumen, el desglose por segmento, las mayores exposiciones y los
créditos vencidos, y se exporta a Excel (`excel_export.py`) con
cuatro hojas. Las cifras salen de las mismas herramientas que usa el
agente para responder, así que lo guardado es exactamente lo que el
agente diría si le preguntaran.

## Tablas dinámicas y Access

El Excel lleva además dos **tablas dinámicas nativas**: «Dinámica por
segmento» (EAD, pérdida esperada y créditos por segmento) y «Dinámica
por estatus» (EAD, pérdida esperada y número de créditos vigente /
vencido dentro del top de exposiciones). Son nativas —definición,
caché y registros dentro del `.xlsx`—, así que Excel las filtra y
recalcula al abrir; si una hoja de origen no tiene filas, su pivote se
salta sin romper la exportación. El helper que las construye está en
`credit_risk_agent/pivot_table.py`.

Y hay una base **real** de Access en `access/credit-risk-agent-adk.accdb`
(formato ACE14): las 4 tablas del snapshot con sus tipos y filas, lista
para abrir en Access. Se regenera con `./access/build_access.sh
snapshots.db credit-risk-agent-adk.accdb` (vuelca a CSV + schema con
`dump_access.py`, construye con Jackcess en Java y verifica con
mdbtools); los detalles y la nota sobre subir el `.accdb` binario por
web están en `access/README.md`. El DDL de referencia sigue en
`sql/schema_access.sql`.

```python
from credit_risk_agent import persistence, excel_export

snap_id = persistence.store_snapshot("snapshots.db")
excel_export.export_workbook("snapshots.db", "cartera.xlsx")
```

## Estructura

```text
credit-risk-agent-adk/
├── credit_risk_agent/
│   ├── __init__.py      # expone root_agent (lo que busca ADK)
│   ├── agent.py         # definición del agente: modelo, instrucción, herramientas
│   ├── tools.py         # cálculo de métricas (EAD, EL, PD, morosidad)
│   ├── data.py          # lectura del CSV (la única puerta a los datos)
│   ├── persistence.py   # SQLite: snapshots de la cartera
│   ├── excel_export.py  # exporta un snapshot a Excel (4 hojas + 2 pivotes)
│   └── pivot_table.py   # tablas dinámicas nativas de Excel (openpyxl)
├── access/              # .accdb real + CSV/schema + constructor (Jackcess)
│   ├── credit-risk-agent-adk.accdb
│   ├── dump_access.py   # vuelca SQLite a CSV + schema
│   ├── AccessBuilder.java / build_access.sh  # construyen el .accdb
│   └── README.md        # cómo regenerarlo y cómo subirlo a GitHub
├── sql/
│   └── schema_access.sql  # DDL para Access (solo esquema, sin probar en Access)
├── data/
│   └── portfolio_sample.csv   # cartera sintética de ejemplo (24 créditos)
├── tests/
│   ├── test_tools.py    # pruebas de las herramientas (sin llave de API)
│   ├── test_persistence.py
│   ├── test_excel_export.py
│   ├── test_access.py
│   └── test_layers.py   # las tres capas no se mezclan + cifras conocidas
├── run_tests.sh         # corre pytest buscando el venv
├── demo.py              # muestra las cifras sin llamar a Gemini
├── requirements.txt
├── .env.example
└── LICENSE
```

## Capas

Tres capas; Bronce/Plata/Oro **no** aplica aquí (el agente lee un solo
CSV pequeño al vuelo y calcula las métricas en el momento; no hay
staging crudo → limpio → agregado que ordenar, así que forzarlo sería
ponerle nombres a algo que no existe):

- **Capa del cliente (presentación)** — `agent.py` (la interfaz con la
  que habla el usuario) y `demo.py`. Nunca tocan los datos ni el
  almacenamiento directo: solo llaman a las herramientas.
- **Capa de reglas de negocio** — `tools.py`: las fórmulas (EL = EAD x
  PD x LGD, PD ponderada, morosidad, desglose por segmento). Son
  funciones puras de Python, probables sin llave de API.
- **Capa de consultas o análisis** — `data.py` (la lectura del CSV),
  `persistence.py` (snapshots en SQLite), `excel_export.py` y
  `pivot_table.py` (más `sql/schema_access.sql` y `access/`).

Nota de frontera: en este proyecto las herramientas SON la superficie
de consulta — el agente le pregunta a la cartera a través de ellas,
no con SQL. Por eso `tools.py` vive en Reglas (es dueño de las
fórmulas) y el lado de lectura/guardado vive en Consultas. La única
dependencia permitida entre esas dos capas es que las reglas lean los
datos (`data.py`); nunca tocan el almacenamiento.

## Datos

La cartera de `data/portfolio_sample.csv` es **sintética**, creada solo para
la demostración: 24 créditos en 4 segmentos (Hipotecario, PyME, Consumo,
Tarjeta) con EAD, PD, LGD y estatus (vigente/vencido). Para usar tus propios
datos, reemplaza ese CSV manteniendo las mismas columnas.

## Notas

- El modelo es `gemini-3.6-flash` (actualizado el 22 nov 2026: Google retiró `gemini-2.0-flash`; `gemini-2.5-flash` ya no está disponible para usuarios nuevos; `gemini-3.7-flash` y `gemini-3.8-flash` estaban saturados con 503; `gemini-3.6-flash` verificado funcionando). Si Google cambia el nombre del modelo,
  actualízalo en `credit_risk_agent/agent.py`.
- La pérdida esperada se calcula como EL = EAD × PD × LGD; la PD ponderada y
  la morosidad se ponderan por exposición (EAD).

## Licencia

MIT. Ver `LICENSE`.
