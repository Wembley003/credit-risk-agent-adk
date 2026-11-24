"""Pruebas de la persistencia en SQLite.

El snapshot guardado tiene que decir exactamente lo mismo que dicen
las herramientas del agente: si el agente responde EAD $17,955,000 y
pérdida esperada $358,595, la base tiene que decir lo mismo. Si algún
día difieren, o cambió el CSV o se rompió algo en el camino, y el
test lo caza.
"""

import pytest

from credit_risk_agent import persistence


def test_snapshot_guarda_las_cifras_del_agente(tmp_path):
    db = tmp_path / "snapshots.db"
    snapshot_id = persistence.store_snapshot(db)
    assert snapshot_id == 1
    snap = persistence.get_snapshot(db, snapshot_id)
    assert snap["numero_creditos"] == 24
    assert snap["ead_total"] == pytest.approx(17_955_000.0)
    assert snap["perdida_esperada_total"] == pytest.approx(358_595.0)
    assert snap["pd_ponderada"] == pytest.approx(0.0430, abs=1e-4)
    assert snap["morosidad_pct"] == pytest.approx(31.30, abs=0.01)


def test_desglose_por_segmento_suma_al_total(tmp_path):
    db = tmp_path / "snapshots.db"
    snapshot_id = persistence.store_snapshot(db)
    snap = persistence.get_snapshot(db, snapshot_id)
    assert {s["segmento"] for s in snap["segmentos"]} == {
        "Consumo", "Hipotecario", "PyME", "Tarjeta",
    }
    assert sum(s["ead_total"] for s in snap["segmentos"]) == pytest.approx(
        snap["ead_total"]
    )
    assert sum(s["perdida_esperada"] for s in snap["segmentos"]) == pytest.approx(
        snap["perdida_esperada_total"]
    )


def test_top_y_vencidos(tmp_path):
    db = tmp_path / "snapshots.db"
    snapshot_id = persistence.store_snapshot(db)
    snap = persistence.get_snapshot(db, snapshot_id)
    assert len(snap["top_exposiciones"]) == 5
    assert snap["top_exposiciones"][0]["id_credito"] == "P-003"
    assert snap["top_exposiciones"][0]["ead"] == pytest.approx(2_500_000.0)
    assert len(snap["vencidos"]) == 8
    assert snap["vencidos"][0]["ead"] == pytest.approx(2_500_000.0)


def test_dos_snapshots_y_get_inexistente(tmp_path):
    db = tmp_path / "snapshots.db"
    id1 = persistence.store_snapshot(db)
    id2 = persistence.store_snapshot(db)
    assert id2 == id1 + 1
    assert len(persistence.list_snapshots(db)) == 2
    assert persistence.get_snapshot(db, 99) is None
