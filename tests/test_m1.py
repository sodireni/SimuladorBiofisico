"""Pruebas del módulo 1 (clima) con respuestas conocidas (valores de referencia de la guía, sección 5)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from simulador.io import cargar_params
from simulador.m1_clima import m1_clima, radiacion_extraterrestre, razon_eto_mensual

RAIZ = str(Path(__file__).resolve().parents[1])


@pytest.fixture
def params():
    return cargar_params(RAIZ)


def _fila(fecha, tmax, tmin, rs=25.0, lat=19.7):
    return pd.DataFrame({"fecha": [pd.Timestamp(fecha)], "lat": [lat], "tmax": [tmax], "tmin": [tmin], "rs": [rs]})


@pytest.mark.parametrize("fecha, esperado", [
    ("2025-03-15", 34.7), ("2025-03-21", 35.5), ("2025-06-21", 39.5),
    ("2025-11-30", 26.4), ("2025-12-21", 25.8)])
def test_ra_a_19_7_grados_coincide_con_la_guia(fecha, esperado):
    assert float(radiacion_extraterrestre(19.7, pd.Timestamp(fecha).dayofyear)) == pytest.approx(esperado, abs=0.06)


def test_ra_reproduce_el_ejemplo_de_fao56():
    # FAO-56, ejemplo 8: 3 de septiembre, 20 °S -> 32.2 MJ/m2/día
    assert float(radiacion_extraterrestre(-20.0, pd.Timestamp("2025-09-03").dayofyear)) == pytest.approx(32.2, abs=0.05)


def test_eto_ejemplo_de_la_guia(params):
    # Tmax 20, Tmin 7, 21-jun, lat 19.7 -> ETo = 4.18 mm/día (sin olvidar el 0.408)
    d = m1_clima(_fila("2025-06-21", 20.0, 7.0), params)
    assert d["eto"].iloc[0] == pytest.approx(4.18, abs=0.01)
    assert d["tmean"].iloc[0] == 13.5


def test_par_es_fraccion_de_rs(params):
    d = m1_clima(_fila("2025-06-21", 20.0, 7.0, rs=25.0), params)
    assert d["par"].iloc[0] == pytest.approx(params["cultivo"]["par_fraccion"] * 25.0)


def test_eto_sin_rango_termico_es_cero_y_nunca_negativa(params):
    d = pd.concat([_fila("2025-06-21", 15.0, 15.0), _fila("2025-06-22", 10.0, 14.0)])  # tmax<tmin: dato inválido
    out = m1_clima(d, params)
    assert (out["eto"] == 0.0).all()


def test_factor_eto_escala_linealmente(params):
    base = m1_clima(_fila("2025-06-21", 20.0, 7.0), params)["eto"].iloc[0]
    con_factor = {**params, "clima": {"factor_eto": 1.1}}
    assert m1_clima(_fila("2025-06-21", 20.0, 7.0), con_factor)["eto"].iloc[0] == pytest.approx(1.1 * base)
    with pytest.raises(ValueError):
        m1_clima(_fila("2025-06-21", 20.0, 7.0), {**params, "clima": {"factor_eto": 0}})


def test_eto_en_rango_razonable_con_datos_sinteticos(entrada, params):
    d = m1_clima(entrada, params)
    assert d["eto"].between(0, 10).all()
    assert 2.0 < d["eto"].mean() < 6.0                                # unos 3-5 mm/día en el Altiplano


def test_no_modifica_la_entrada_y_conserva_filas(entrada, params):
    copia = entrada.copy()
    d = m1_clima(entrada, params)
    pd.testing.assert_frame_equal(entrada, copia)
    assert len(d) == len(entrada) and (d.index == entrada.index).all()


def test_errores_claros(params):
    with pytest.raises(KeyError):
        m1_clima(_fila("2025-06-21", 20, 7).drop(columns=["rs"]), params)
    malo = _fila("2025-06-21", np.nan, 7)
    with pytest.raises(ValueError):
        m1_clima(malo, params)


def test_razon_mensual_con_caso_simple():
    d = pd.DataFrame({"fecha": pd.to_datetime(["2025-04-01", "2025-04-02", "2025-05-01"]),
                      "eto": [4.0, 4.0, 3.0], "eto_om": [5.0, 5.0, 3.0]})
    r = razon_eto_mensual(d)
    assert r.loc[4] == pytest.approx(0.8) and r.loc[5] == pytest.approx(1.0)
