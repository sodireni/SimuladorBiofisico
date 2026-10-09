"""
Plantillas de prueba por módulo. Hoy salen como 'xfail' (esperadas a fallar) porque los módulos
no están implementados. Cuando implementen el suyo: QUITEN el decorador @pendiente de sus pruebas,
confirmen que pasan y AGREGUEN sus propias pruebas (casos con respuesta conocida).
"""
from pathlib import Path

import numpy as np
import pytest

from simulador.io import cargar_params

from simulador.m1_clima import m1_clima
from simulador.m2_fenologia import ESTADIOS, m2_fenologia
from simulador.m3_balance_hidrico import m3_balance_hidrico
from simulador.m4_lue import m4_lue

pendiente = pytest.mark.xfail(raises=NotImplementedError, reason="módulo sin implementar")
PARAMS = cargar_params(str(Path(__file__).resolve().parents[1]))   # configs/params.yaml


@pendiente
def test_m1_agrega_columnas_y_rangos(entrada):
    d = m1_clima(entrada, PARAMS)
    for c in ["tmean", "ra", "par", "eto"]:
        assert c in d.columns and d[c].notna().all()
    assert len(d) == len(entrada)
    assert (d["eto"] >= 0).all() and (d["ra"] > 0).all()
    assert np.allclose(d["tmean"], (entrada["tmax"] + entrada["tmin"]) / 2)


@pendiente
def test_m2_agrega_columnas_y_estadios(entrada_m1_m2):
    entrada = entrada_m1_m2.drop(columns=["gdd_acum", "estadio", "kc", "fecha_antesis", "fecha_madurez"])
    d = m2_fenologia(entrada, PARAMS)
    assert set(d["estadio"].unique()) <= set(ESTADIOS)
    assert (d["gdd_acum"] >= 0).all() and d["kc"].between(0, 1.3).all()
    assert (d.loc[d["fecha"] < d["fecha_siembra"], "gdd_acum"] == 0).all()
    assert (d.groupby("ID_POLIGON")["gdd_acum"].diff().dropna() >= 0).all()      # monótona


def test_m3_limites_y_balance(entrada_m3):
    entrada = entrada_m3.drop(columns=["sw", "ks", "eta"])
    d = m3_balance_hidrico(entrada, PARAMS)
    assert d["ks"].between(0, 1).all()
    assert (d["sw"] >= d["PWP_mm"] - 1e-9).all() and (d["sw"] <= d["FC_mm"] + 1e-9).all()
    assert (d["eta"] <= d["eto"] * d["kc"] + 1e-9).all()


@pendiente
def test_m4_biomasa_no_decrece(entrada_m3):
    d = m4_lue(entrada_m3, PARAMS)
    assert (d["dbio"] >= 0).all()
    assert (d.groupby("ID_POLIGON")["bio"].diff().dropna() >= -1e-9).all()
