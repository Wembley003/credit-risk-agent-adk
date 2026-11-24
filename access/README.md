# Access (.accdb) del agente de riesgo de crédito

`credit-risk-agent-adk.accdb` es una base **real** de Microsoft Access
(formato ACE14, Access 2010 en adelante) con las mismas 4 tablas del
snapshot en SQLite: `snapshots`, `segmentos`, `top_exposiciones` y
`vencidos`, con sus tipos y sus filas. Se abre en Access tal cual, sin
importar nada a mano: doble clic y las tablas ya están ahí.

## Cómo se regenera

En Linux no hay Access, así que el `.accdb` se construye en dos pasos
con Java (Jackcess escribe el formato ACE14 sin necesitar Windows):

```bash
# 1. Guarda un snapshot en SQLite (si no tienes uno ya)
python -c "from credit_risk_agent import persistence; persistence.store_snapshot('snapshots.db')"

# 2. Construye el .accdb (vuelca a CSV + schema, compila y verifica)
./access/build_access.sh snapshots.db credit-risk-agent-adk.accdb
```

El script hace todo solo: vuelca las tablas a `access/csv/*.csv` con
`dump_access.py`, descarga los jars de Jackcess a `access/lib/` la
primera vez, compila `AccessBuilder.java` y verifica con `mdbtools`
que cada tabla del `.accdb` tenga las mismas filas que su CSV. Necesita
Python 3, JDK 17, `curl` y conexión la primera vez (para los jars).

## Cómo se abre en Access

Copia el `.accdb` a Windows y ábrelo con Microsoft Access. Las tablas
están listas para consultar; las relaciones entre `snapshots.id` y
`snapshot_id` de las demás tablas se crean en Herramientas de base de
datos > Relaciones (el DDL de referencia está en `sql/schema_access.sql`).

## Nota honesta: el `.accdb` es binario

El push por lotes de GitHub solo lleva archivos de texto, así que el
`.accdb` **no** se puede subir por esa vía: súbelo por web desde el
celular (Add file > Upload files en github.com), igual que los PNG.
Lo que sí viaja en texto —y es el pack de importación si alguien
quiere reconstruir la base a mano— son `access/csv/*.csv` más
`access/schema.txt` y `access/schema.json`: con esos tres, Access
importa cada tabla con su tipo correcto sin adivinar nada.

`access/lib/` (los jars descargados) y `access/build/` (los `.class`
compilados) no van a Git: se regeneran solos al correr el script.
