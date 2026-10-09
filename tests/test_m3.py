"""Pruebas del módulo 3 (balance hídrico) con respuestas conocidas hechas a mano."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from simulador.io import cargar_params
from simulador.m3_balance_hidrico import m3_balance_hidrico

RAIZ = str(Path(__file__).resolve().parents[1])
FC, PWP, AWC = 154.0, 92.0, 62.0          # AWC = FC - PWP
P = 0.55                                  # umbral de estrés = FC - P*AWC = 119.9 mm


@pytest.fixture
def params():
    return cargar_params(RAIZ)


def _caso(pcp, eto=4.0, kc=1.0, id_="AGC_001", fc=FC, pwp=PWP, awc=AWC):
    pcp = np.asarray(pcp, float)
    n = len(pcp)
    return pd.DataFrame({
        "ID_POLIGON": id_, "fecha": pd.date_range("2025-03-15", periods=n),
        "pcp": pcp, "eto": np.full(n, eto), "kc": np.full(n, kc),
        "FC_mm": fc, "PWP_mm": pwp, "AWC_mm": awc})


def _con(params, **cambios):
    """Copia de params con valores sustituidos: _con(params, frac=0.3, p=0.5)."""
    nuevo = {k: dict(v) if isinstance(v, dict) else v for k, v in params.items()}
    if "frac" in cambios:
        nuevo["suelo"]["sw_inicial_frac_awc"] = cambios["frac"]
    if "p" in cambios:
        nuevo["cultivo"]["p_agotamiento"] = cambios["p"]
    return nuevo


def test_un_dia_a_mano_usa_el_sw_del_dia_anterior(params):
    # frac=0.3 -> sw0 = 92 + 0.3*62 = 110.6 < 119.9 (hay estrés)
    # ks = (110.6 - 92) / ((1-0.55)*62) = 18.6 / 27.9 = 2/3 ; eta = 4*1*2/3 ; sw = 110.6 - eta
    d = m3_balance_hidrico(_caso([0.0]), _con(params, frac=0.3))
    assert d["ks"].iloc[0] == pytest.approx(2 / 3)
    assert d["eta"].iloc[0] == pytest.approx(8 / 3)
    assert d["sw"].iloc[0] == pytest.approx(110.6 - 8 / 3)


def test_sin_estres_si_el_suelo_empieza_humedo(params):
    # frac=1.0 -> sw0 = FC: ks = 1 y eta = eto*kc el primer día
    d = m3_balance_hidrico(_caso([0.0]), _con(params, frac=1.0))
    assert d["ks"].iloc[0] == 1.0 and d["eta"].iloc[0] == pytest.approx(4.0)


def test_ks_es_continuo_en_el_umbral(params):
    # sw0 justo en el umbral FC - p*AWC: la fórmula de abajo también da 1
    frac = (FC - P * AWC - PWP) / AWC
    d = m3_balance_hidrico(_caso([0.0]), _con(params, frac=frac))
    assert d["ks"].iloc[0] == pytest.approx(1.0)


def test_sin_lluvia_el_suelo_se_seca_hasta_pwp_y_ks_tiende_a_cero(params):
    d = m3_balance_hidrico(_caso(np.zeros(250), eto=5.0), params)
    assert d["ks"].iloc[-1] < 1e-6                      # el decaimiento es exponencial: tiende a 0
    assert d["sw"].iloc[-1] == pytest.approx(PWP, abs=1e-4)
    assert (d["ks"].diff().dropna() <= 1e-12).all()      # nunca se recupera sin lluvia


def test_con_lluvia_muy_alta_el_suelo_queda_en_fc(params):
    d = m3_balance_hidrico(_caso(np.full(30, 80.0)), params)
    assert (d["sw"] == FC).all() and (d["ks"] == 1.0).all()


def test_cierre_del_balance_sin_drenaje(params):
    # lluvia escasa: el suelo nunca llega a FC, así que no hay drenaje y el cierre es exacto
    pcp = np.zeros(90)
    pcp[::3] = 1.0
    d = m3_balance_hidrico(_caso(pcp, eto=3.0, kc=0.8), params)
    sw0 = PWP + params["suelo"]["sw_inicial_frac_awc"] * AWC
    assert (d["sw"] < FC).all()
    assert d["pcp"].sum() - d["eta"].sum() == pytest.approx(d["sw"].iloc[-1] - sw0, abs=1e-9)


def test_cierre_del_balance_con_drenaje(params):
    # drenaje implícito = sw_prev + pcp - eta - sw; debe ser >= 0 y solo ocurrir cuando sw = FC
    rng = np.random.default_rng(1)
    pcp = np.where(rng.random(261) < 0.4, rng.gamma(1.2, 9, 261), 0.0)
    d = m3_balance_hidrico(_caso(pcp, eto=3.5, kc=0.9), params)
    sw0 = PWP + params["suelo"]["sw_inicial_frac_awc"] * AWC
    sw_prev = np.r_[sw0, d["sw"].to_numpy()[:-1]]
    drenaje = sw_prev + d["pcp"].to_numpy() - d["eta"].to_numpy() - d["sw"].to_numpy()
    assert (drenaje >= -1e-9).all()
    assert drenaje.sum() > 0                                           # el caso sí produce drenaje
    assert np.allclose(drenaje[d["sw"].to_numpy() < FC - 1e-9], 0.0, atol=1e-9)
    assert d["pcp"].sum() - d["eta"].sum() - drenaje.sum() == pytest.approx(d["sw"].iloc[-1] - sw0, abs=1e-6)


def test_limites_con_datos_sinteticos(entrada_m3, params):
    entrada = entrada_m3.drop(columns=["sw", "ks", "eta"])
    d = m3_balance_hidrico(entrada, params)
    assert d[["sw", "ks", "eta"]].notna().all().all()
    assert d["ks"].between(0, 1).all()
    assert (d["sw"] >= d["PWP_mm"] - 1e-9).all() and (d["sw"] <= d["FC_mm"] + 1e-9).all()
    assert (d["eta"] <= d["eto"] * d["kc"] + 1e-9).all() and (d["eta"] >= 0).all()


def test_parcelas_independientes_orden_e_inmutabilidad(entrada_m3, params):
    entrada = entrada_m3.drop(columns=["sw", "ks", "eta"])
    copia = entrada.copy()
    juntas = m3_balance_hidrico(entrada, params)
    pd.testing.assert_frame_equal(entrada, copia)                      # no modifica la entrada

    sola = m3_balance_hidrico(entrada[entrada["ID_POLIGON"] == "AGC_002"], params)
    ref = juntas[juntas["ID_POLIGON"] == "AGC_002"]
    np.testing.assert_allclose(sola[["sw", "ks", "eta"]].to_numpy(), ref[["sw", "ks", "eta"]].to_numpy())

    revuelto = entrada.sample(frac=1.0, random_state=3)                # filas desordenadas
    r = m3_balance_hidrico(revuelto, params).sort_index()
    np.testing.assert_allclose(r[["sw", "ks", "eta"]].to_numpy(), juntas[["sw", "ks", "eta"]].to_numpy())


def test_mas_agua_inicial_no_baja_la_eta_acumulada(params):
    d = _caso(np.zeros(60), eto=4.0)
    eta = {f: m3_balance_hidrico(d, _con(params, frac=f))["eta"].sum() for f in (0.3, 0.5, 0.8)}
    assert eta[0.3] <= eta[0.5] <= eta[0.8]


def test_errores_claros(params):
    d = _caso([0.0, 1.0])
    with pytest.raises(KeyError):
        m3_balance_hidrico(d.drop(columns=["kc"]), params)
    con_nan = d.copy()
    con_nan.loc[0, "pcp"] = np.nan
    with pytest.raises(ValueError):
        m3_balance_hidrico(con_nan, params)
    with pytest.raises(ValueError):
        m3_balance_hidrico(pd.concat([d, d]), params)                  # fecha repetida
