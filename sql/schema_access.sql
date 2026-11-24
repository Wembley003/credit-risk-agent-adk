-- Esquema para Microsoft Access (.accdb): snapshots, segmentos,
-- top_exposiciones y vencidos.
--
-- Esto es SOLO el esquema (DDL), no una integración con Access. No hay
-- base .accdb aquí y no se ejecutó en Access: en Linux no hay Access.
-- Para usarlo: en Access, Crear > Diseño de consulta > vista SQL,
-- pegar este script y ejecutarlo; las relaciones se crean después en
-- Herramientas de base de datos > Relaciones.

CREATE TABLE snapshots (
    id                      AUTOINCREMENT PRIMARY KEY,
    created_at              DATETIME NOT NULL,
    numero_creditos         LONG NOT NULL,
    ead_total               DOUBLE NOT NULL,
    perdida_esperada_total  DOUBLE NOT NULL,
    pd_ponderada            DOUBLE NOT NULL,
    cartera_vencida         DOUBLE NOT NULL,
    morosidad_pct           DOUBLE NOT NULL
);

CREATE TABLE segmentos (
    id               AUTOINCREMENT PRIMARY KEY,
    snapshot_id      LONG NOT NULL,
    segmento         TEXT(30) NOT NULL,
    numero_creditos  LONG NOT NULL,
    ead_total        DOUBLE NOT NULL,
    perdida_esperada DOUBLE NOT NULL,
    pd_ponderada     DOUBLE NOT NULL,
    morosidad_pct    DOUBLE NOT NULL
);

CREATE TABLE top_exposiciones (
    id                AUTOINCREMENT PRIMARY KEY,
    snapshot_id       LONG NOT NULL,
    puesto            LONG NOT NULL,
    id_credito        TEXT(20) NOT NULL,
    segmento          TEXT(30) NOT NULL,
    ead               DOUBLE NOT NULL,
    pd                DOUBLE NOT NULL,
    lgd               DOUBLE NOT NULL,
    perdida_esperada  DOUBLE NOT NULL,
    estatus           TEXT(20) NOT NULL
);

CREATE TABLE vencidos (
    id           AUTOINCREMENT PRIMARY KEY,
    snapshot_id  LONG NOT NULL,
    id_credito   TEXT(20) NOT NULL,
    segmento     TEXT(30) NOT NULL,
    ead          DOUBLE NOT NULL,
    pd           DOUBLE NOT NULL,
    lgd          DOUBLE NOT NULL
);
