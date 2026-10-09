"""Pruebas del módulo 2 (fenología) con respuestas conocidas hechas a mano (guía, sección 6)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from simulador.io import cargar_params
from simulador.m2_fenologia import ESTADIOS, ciclos_incompletos, m2_fenologia

RAIZ = str(Path(__file__).resolve().parents[1])
SIEMBRA = pd.Timestamp("2025-04-01")


@pytest.fixture
def params():
    return cargar_params(RAIZ)


def _con(params, **fen):
    nuevo = {k: dict(v) for k, v in params.items()}
    nuevo["fenologia"].update(fen)
    return nuevo


def _serie(tmean=10.0, n=220, siembra=SIEMBRA, id_="AGC_001", **extra):
    f = pd.date_range("2025-03-15", periods=n)
    d = pd.DataFrame({"ID_POLIGON": id_, "fecha": f, "tmean": tmean, "fecha_siembra": siembra})
    for k, v in extra.items():
        d[k] = v
    return d


def _dia(d, k):
    """Fila de la serie a k días de la siembra."""
    return d[d["fecha"] == SIEMBRA + pd.Timedelta(days=k)].iloc[0]


def test_gdd_crece_10_por_dia_y_es_cero_antes_de_sembrar(params):
    p = _con(params, tbase_c=0.0)
    d = m2_fenologia(_serie(tmean=10.0), p)
    assert (d.loc[d["fecha"] < SIEMBRA, "gdd_acum"] == 0).all()
    assert _dia(d, 0)["gdd_acum"] == 10.0 and _dia(d, 9)["gdd_acum"] == 100.0
    assert (d["gdd_acum"].diff().dropna() >= 0).all()


def test_tbase_2_reduce_los_gdd_diarios(params):
    d = m2_fenologia(_serie(tmean=10.0), _con(params, tbase_c=2.0))
    assert _dia(d, 9)["gdd_acum"] == pytest.approx(80.0)                # 8 °C·d por día
    frio = m2_fenologia(_serie(tmean=1.0), _con(params, tbase_c=2.0))    # bajo Tbase: no acumula
    assert (frio["gdd_acum"] == 0).all()


def test_umbral_gdd_fechas_conocidas(params):
    # 10 °C·d/día, Tbase 0: 800 °C·d se alcanzan al día 80 (k=79); 1450 al día 145 (k=144)
    d = m2_fenologia(_serie(tmean=10.0), _con(params, tbase_c=0.0, modo="umbral_gdd"))
    assert d["fecha_antesis"].iloc[0] == SIEMBRA + pd.Timedelta(days=79)
    assert d["fecha_madurez"].iloc[0] == SIEMBRA + pd.Timedelta(days=144)
    assert d["fecha_antesis"].nunique() == 1 and d["fecha_madurez"].nunique() == 1


def test_estadios_con_prioridad_de_la_ventana_de_antesis(params):
    d = m2_fenologia(_serie(tmean=10.0), _con(params, tbase_c=0.0, ventana_antesis_dias=10))
    assert set(d["estadio"]) <= set(ESTADIOS)
    assert _dia(d, -1)["estadio"] == "pre_siembra"
    assert _dia(d, 0)["estadio"] == "vegetativo" and _dia(d, 68)["estadio"] == "vegetativo"
    assert _dia(d, 69)["estadio"] == "antesis" and _dia(d, 89)["estadio"] == "antesis"   # 79 +- 10
    assert _dia(d, 90)["estadio"] == "llenado" and _dia(d, 144)["estadio"] == "llenado"  # inclusive
    assert _dia(d, 145)["estadio"] == "madurez"


def test_kc_por_tramos(params):
    c = params["cultivo"]
    d = m2_fenologia(_serie(tmean=10.0), _con(params, tbase_c=0.0))
    assert _dia(d, -5)["kc"] == pytest.approx(c["kc_ini"])              # suelo desnudo antes de sembrar
    assert _dia(d, 10)["kc"] == pytest.approx(c["kc_ini"])              # tramo inicial (30 % de 79 d = 23.7 d)
    assert _dia(d, 79)["kc"] == pytest.approx(c["kc_mid"])              # en la antesis
    assert all(_dia(d, k)["kc"] == pytest.approx(c["kc_mid"]) for k in range(79, 111))   # meseta mid
    assert _dia(d, 144)["kc"] == pytest.approx(c["kc_end"])             # en la madurez
    assert _dia(d, 200)["kc"] == pytest.approx(c["kc_end"])             # después de la madurez
    desarrollo = [_dia(d, k)["kc"] for k in range(24, 80)]
    tardio = [_dia(d, k)["kc"] for k in range(112, 145)]
    assert np.all(np.diff(desarrollo) > 0) and np.all(np.diff(tardio) < 0)


def test_madurez_no_alcanzada_usa_el_ultimo_dia_y_se_marca(params):
    d = m2_fenologia(_serie(tmean=10.0, n=90), _con(params, tbase_c=0.0))   # solo ~74 días de cultivo
    assert d["fecha_antesis"].iloc[0] == d["fecha"].max() == d["fecha_madurez"].iloc[0]
    marca = ciclos_incompletos(d)
    assert marca["madurez_incompleta"].all() and marca["antesis_incompleta"].all()
    completo = ciclos_incompletos(m2_fenologia(_serie(tmean=10.0), _con(params, tbase_c=0.0)))
    assert not completo["madurez_incompleta"].any()


def test_modo_satelite_fechas_conocidas(params):
    # fapar: sube hasta el pico (día 70 desde siembra, 0.8) y cae 0.02 por día; madurez cuando <= 0.5*0.8 = 0.4
    f = pd.date_range("2025-03-15", periods=220)
    k = (f - SIEMBRA).days.to_numpy()
    fapar = np.where(k <= 70, 0.8 * np.clip(k, 0, None) / 70, 0.8 - 0.02 * (k - 70))
    pico = SIEMBRA + pd.Timedelta(days=70)
    d = m2_fenologia(_serie(tmean=10.0, fapar_final=fapar, fecha_pico=pico),
                     _con(params, tbase_c=0.0, modo="satelite", madurez_fapar_frac_pico=0.5))
    assert d["fecha_antesis"].iloc[0] == pico
    assert d["fecha_madurez"].iloc[0] == pico + pd.Timedelta(days=20)    # 0.8 - 0.02*20 = 0.4
    with pytest.raises(KeyError):                                         # falta fecha_pico / fapar_final
        m2_fenologia(_serie(), _con(params, modo="satelite"))


def test_parcelas_independientes_orden_e_inmutabilidad(params):
    a = _serie(tmean=10.0, id_="AGC_001")
    b = _serie(tmean=14.0, id_="AGC_002", siembra=pd.Timestamp("2025-05-01"))
    junto = pd.concat([a, b], ignore_index=True)
    copia = junto.copy()
    p = _con(params, tbase_c=0.0)
    r = m2_fenologia(junto, p)
    pd.testing.assert_frame_equal(junto, copia)
    sola = m2_fenologia(b, p)
    np.testing.assert_allclose(sola["gdd_acum"], r[r["ID_POLIGON"] == "AGC_002"]["gdd_acum"])
    barajado = m2_fenologia(junto.sample(frac=1.0, random_state=2), p).sort_index()
    np.testing.assert_allclose(barajado["gdd_acum"], r["gdd_acum"])
    assert (barajado["estadio"] == r["estadio"]).all()
    assert r.groupby("ID_POLIGON")["fecha_antesis"].nunique().eq(1).all()


def test_errores_claros(params):
    with pytest.raises(KeyError):
        m2_fenologia(_serie().drop(columns=["tmean"]), params)
    with pytest.raises(ValueError):
        m2_fenologia(_serie(), _con(params, modo="otro"))
    sin_siembra = _serie()
    sin_siembra.loc[0, "fecha_siembra"] = pd.NaT
    with pytest.raises(ValueError):
        m2_fenologia(sin_siembra, params)
