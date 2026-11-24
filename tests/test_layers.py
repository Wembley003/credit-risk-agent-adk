"""Pruebas de la estructura por capas del agente ADK.

Las tres capas del proyecto (Bronce/Plata/Oro NO aplica aquí: el
agente lee un solo CSV pequeño al vuelo y calcula las métricas en el
momento; no hay staging crudo → limpio → agregado que ordenar):

    Cliente (presentación): agent.py, demo.py
                            (la interfaz con la que habla el usuario)
    Reglas de negocio:      tools.py
                            (las fórmulas: EL = EAD x PD x LGD, PD
                            ponderada, morosidad, desglose por segmento)
    Consultas o análisis:   data.py, persistence.py, excel_export.py,
                            pivot_table.py (la lectura del CSV, los
                            snapshots en SQLite y las exportaciones)

Nota de frontera: en este proyecto las herramientas SON la superficie
de consulta — el agente le pregunta a la cartera a través de ellas,
no con SQL. Por eso tools.py vive en Reglas (es dueño de las
fórmulas) y el lado de lectura/guardado vive en Consultas. La
dependencia permitida es una sola: las reglas leen los datos
(data.py), pero nunca tocan el almacenamiento (persistence, Excel).
"""

import ast
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from credit_risk_agent import agent, tools

_PROJECT = Path(__file__).resolve().parent.parent
_PACKAGE = _PROJECT / "credit_risk_agent"
_PAQUETE = "credit_risk_agent"

_CAPAS = {
    "cliente": {"agent", "demo"},
    "reglas": {"tools"},
    "consultas": {"data", "persistence", "excel_export", "pivot_table"},
}
# Módulos de almacenamiento/salida que las reglas no deben conocer.
_SALIDA = {"persistence", "excel_export", "pivot_table"}
# Librerías de almacenamiento/salida que cliente y reglas no deben importar.
_LIBS_SALIDA = {"openpyxl", "sqlite3"}


def test_herramientas_dan_las_cifras_conocidas():
    # Las reglas calculan las cifras que el agente responde: las
    # mismas del ETL de Spark y del tablero.
    resumen = tools.resumen_cartera()
    assert resumen["numero_creditos"] == 24
    assert resumen["ead_total"] == pytest.approx(17_955_000)
    assert resumen["perdida_esperada_total"] == pytest.approx(358_595)
    assert resumen["pd_ponderada"] == pytest.approx(0.0430)
    assert resumen["morosidad_pct"] == pytest.approx(31.30)


def test_desglose_por_segmento_suma_al_total():
    # El desglose por segmento suma al total: la capa de Reglas no
    # puede contradecirse a sí misma.
    resumen = tools.resumen_cartera()
    segmentos = tools.desglose_por_segmento()
    assert sum(s["ead_total"] for s in segmentos.values()) == pytest.approx(
        resumen["ead_total"]
    )
    assert sum(s["perdida_esperada"] for s in segmentos.values()) == pytest.approx(
        resumen["perdida_esperada_total"]
    )
    assert sum(s["numero_creditos"] for s in segmentos.values()) == 24


def test_el_agente_solo_usa_las_herramientas():
    # El agente no tiene otra fuente de cifras: sus herramientas son
    # exactamente las cuatro funciones del módulo de reglas, las
    # mismas que acabamos de probar. Si mañana se agrega una
    # herramienta, hay que agregarla aquí y en agent.py a la vez.
    assert agent.root_agent.tools == [
        tools.resumen_cartera,
        tools.desglose_por_segmento,
        tools.mayores_exposiciones,
        tools.creditos_vencidos,
    ]
    # Y lo que el agente respondería con una herramienta es lo mismo
    # que da la función llamada directamente.
    assert agent.root_agent.tools[0]() == tools.resumen_cartera()


# --- Las capas no se mezclan (análisis estático de imports) -------------

def _modulos_importados(path: Path) -> set[str]:
    """Nombres de módulo que un archivo importa (resueltos a su raíz)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nombres = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                partes = alias.name.split(".")
                nombres.add(partes[1] if partes[0] == _PAQUETE and len(partes) > 1 else partes[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                partes = node.module.split(".")
                nombres.add(partes[1] if partes[0] == _PAQUETE and len(partes) > 1 else partes[0])
            else:
                for alias in node.names:
                    nombres.add(alias.name.split(".")[0])
    return nombres


def _capa_de(stem: str) -> str:
    for capa, modulos in _CAPAS.items():
        if stem in modulos:
            return capa
    raise AssertionError(f"módulo sin capa asignada: {stem}")


def test_todos_los_modulos_tienen_capa():
    # Cada módulo del paquete pertenece a exactamente una capa; si
    # alguien agrega un archivo y se le olvida ubicarlo, esta prueba
    # lo delata. __init__.py es la fachada pública, no una capa.
    vistos = set()
    for path in sorted(_PACKAGE.glob("*.py")):
        if path.stem == "__init__":
            continue
        vistos.add(path.stem)
        _capa_de(path.stem)
    assert vistos == _CAPAS["reglas"] | _CAPAS["consultas"] | {"agent"}
    assert (_PROJECT / "demo.py").exists()


def test_capas_no_se_mezclan():
    # Cliente: solo habla con las reglas, nunca toca los datos ni el
    # almacenamiento directo. Reglas: leen los datos (data.py) pero
    # no conocen el almacenamiento. Consultas: sin llamar al cliente.
    archivos = {p.stem: p for p in _PACKAGE.glob("*.py")}
    archivos["demo"] = _PROJECT / "demo.py"
    for stem, path in sorted(archivos.items()):
        if stem == "__init__":
            continue
        capa = _capa_de(stem)
        importados = _modulos_importados(path)
        if capa == "cliente":
            assert not (importados & _CAPAS["consultas"]), (
                f"{stem} (cliente) importa de consultas: {importados & _CAPAS['consultas']}"
            )
            assert not (importados & _LIBS_SALIDA), (
                f"{stem} (cliente) importa librerías de salida: {importados & _LIBS_SALIDA}"
            )
        elif capa == "reglas":
            assert not (importados & _SALIDA), (
                f"{stem} (reglas) importa módulos de salida: {importados & _SALIDA}"
            )
            assert not (importados & _CAPAS["cliente"]), (
                f"{stem} (reglas) importa del cliente: {importados & _CAPAS['cliente']}"
            )
            assert not (importados & _LIBS_SALIDA), (
                f"{stem} (reglas) importa librerías de salida: {importados & _LIBS_SALIDA}"
            )
        elif capa == "consultas":
            assert not (importados & _CAPAS["cliente"]), (
                f"{stem} (consultas) importa del cliente: {importados & _CAPAS['cliente']}"
            )


def test_reglas_no_dependen_del_formato_de_salida():
    # La prueba fuerte: con openpyxl y sqlite3 bloqueados, las reglas
    # siguen dando las cifras conocidas. Si el cálculo dependiera de
    # Excel o de la base, esto se cae.
    codigo = textwrap.dedent(
        """
        import importlib.abc
        import sys
        sys.path.insert(0, r"%s")

        class _Bloqueo(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".")[0] in {"openpyxl", "sqlite3"}:
                    raise ImportError("bloqueado en esta prueba: " + fullname)
                return None

        sys.meta_path.insert(0, _Bloqueo())
        from credit_risk_agent import tools
        resumen = tools.resumen_cartera()
        assert resumen["numero_creditos"] == 24
        assert resumen["ead_total"] == 17_955_000
        assert resumen["perdida_esperada_total"] == 358_595
        print("reglas OK sin openpyxl ni sqlite3")
        """
        % str(_PROJECT)
    )
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT),
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "reglas OK sin openpyxl ni sqlite3" in resultado.stdout
