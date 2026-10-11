"""Pruebas del módulo 4 (biomasa por LUE y HI) con respuestas conocidas hechas a mano (guía, sección 8)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from simulador.io import cargar_params
from simulador.m4_lue import hi_penalizado, m4_lue

RAIZ = str(Path(__file__).resolve().parents[1])
SIEMBRA = pd.Timestamp("2025-04-01")
MADUREZ = pd.Timestamp("2025-06-30")           # 90 días después de la siembra


@pytest.fixture
def params():
    return cargar_params(RAIZ)


def _con(params, **cambios):
    nuevo = {k: (dict(v) if isinstance(v, dict) else v) for k, v in params.items()}
    for ruta, valor in cambios.items():
        seccion, clave = ruta.split("__")
        nuevo[seccion][clave] = valor
    return nuevo


def _serie(par=10.0, fapar=0.5, ks=0.8, n=150, id_="AGC_001", madurez=MADUREZ):
    f = pd.date_range("2025-03-15", periods=n)
    return pd.DataFrame({"ID_POLIGON": id_, "fecha": f, "par": par, "fapar_final": fapar, "ks": ks,
                         "fecha_siembra": SIEMBRA, "fecha_madurez": madurez})


def test_dbio_a_mano_y_acumulacion_solo_en_el_ciclo(params):
    # dbio = 10 * 0.5 * 2.5 * 0.8 * 10 = 100 kg/ha/día; el ciclo (siembra..madurez, ambos) dura 91 días
    d = m4_lue(_serie(), _con(params, cultivo__rue_max_g_mj_par=2.5))
    en = (d["fecha"] >= SIEMBRA) & (d["fecha"] <= MADUREZ)
    assert np.allclose(d.loc[en, "dbio"], 100.0)
    assert (d.loc[~en, "dbio"] == 0).all()                                     # nada antes de sembrar ni después de madurar
    assert d.loc[d["fecha"] == MADUREZ, "bio"].iloc[0] == pytest.approx(91 * 100.0)
    assert np.allclose(d.loc[d["fecha"] >= MADUREZ, "bio"], 9100.0)              # constante después de la madurez
    assert (d.loc[d["fecha"] < SIEMBRA, "bio"] == 0).all()


def test_sin_fpar_o_sin_ks_no_hay_biomasa(params):
    assert (m4_lue(_serie(fapar=0.0), params)["bio"] == 0).all()
    assert (m4_lue(_serie(ks=0.0), params)["bio"] == 0).all()


def test_duplicar_par_duplica_dbio_y_rue_escala_linealmente(params):
    a = m4_lue(_serie(par=10.0), params)
    b = m4_lue(_serie(par=20.0), params)
    np.testing.assert_allclose(b["dbio"], 2 * a["dbio"])
    c = m4_lue(_serie(), _con(params, cultivo__rue_max_g_mj_par=2 * params["cultivo"]["rue_max_g_mj_par"]))
    assert a["bio"].max() > 0
    np.testing.assert_allclose(c["bio"], 2 * a["bio"])                           # RUE x2 -> biomasa x2


def test_fapar_mayor_a_1_se_acota(params):
    a = m4_lue(_serie(fapar=1.0), params)
    b = m4_lue(_serie(fapar=1.7), params)
    np.testing.assert_allclose(a["dbio"], b["dbio"])


def test_bio_es_monotona_y_cada_parcela_acumula_por_separado(params):
    a = _serie(id_="AGC_001", ks=0.8)
    b = _serie(id_="AGC_002", ks=0.4)
    junto = pd.concat([a, b], ignore_index=True)
    copia = junto.copy()
    r = m4_lue(junto, params)
    pd.testing.assert_frame_equal(junto, copia)                                # no modifica la entrada
    assert (r.groupby("ID_POLIGON")["bio"].diff().dropna() >= -1e-9).all()
    fin_b = r[(r["ID_POLIGON"] == "AGC_002") & (r["fecha"] == MADUREZ)]["bio"].iloc[0]
    sola = m4_lue(b, params)
    assert fin_b == pytest.approx(sola.loc[sola["fecha"] == MADUREZ, "bio"].iloc[0])   # no hereda la biomasa de AGC_001
    barajado = m4_lue(junto.sample(frac=1.0, random_state=4), params).sort_index()
    np.testing.assert_allclose(barajado["bio"], r["bio"])


def test_errores_claros(params):
    with pytest.raises(KeyError):
        m4_lue(_serie().drop(columns=["ks"]), params)
    with pytest.raises(ValueError):
        m4_lue(_serie(ks=1.2), params)
    with pytest.raises(ValueError):
        m4_lue(pd.concat([_serie(), _serie()]), params)                        # fechas repetidas


def test_hi_opcion_A_a_mano(params):
    p = _con(params, lue__hi_opcion="A", cultivo__hi_base=0.45, lue__hi_beta=0.5)
    assert hi_penalizado(4000, 10000, 0.6, p) == pytest.approx(0.45 * (1 - 0.5 * 0.4))      # 0.36
    assert hi_penalizado(4000, 10000, 1.0, p) == pytest.approx(0.45)


def test_hi_opcion_B_kemanian_a_mano(params):
    p = _con(params, lue__hi_opcion="B")
    p["lue"]["hi_kemanian"] = {"hi0": 0.3, "s": 0.3}
    # fG = (10000 - 4000) / 10000 = 0.6 -> HI = 0.3 + 0.3 * 0.6 = 0.48
    assert hi_penalizado(4000, 10000, 0.9, p) == pytest.approx(0.48)
    assert hi_penalizado(10000, 10000, 0.9, p) == pytest.approx(0.30)                       # sin biomasa posterior a la antesis
    assert hi_penalizado(0, 0, 0.9, p) == pytest.approx(0.30)                               # sin biomasa: no divide entre 0


def test_hi_opcion_C_a_mano_y_acotada(params):
    p = _con(params, lue__hi_opcion="C", cultivo__hi_base=0.45, lue__hi_sens_antesis=0.5, lue__hi_sens_llenado=0.3)
    # 0.45 * (1 - 0.5*(1-0.8) - 0.3*(1-0.6)) = 0.45 * 0.78 = 0.351
    assert hi_penalizado(4000, 10000, 0.6, p, ks_prom_antesis=0.8) == pytest.approx(0.351)
    assert hi_penalizado(4000, 10000, 1.0, p, ks_prom_antesis=1.0) == pytest.approx(0.45)   # sin estrés: HI_base
    assert 0.0 <= hi_penalizado(4000, 10000, 0.0, p, ks_prom_antesis=0.0) <= 0.45
    with pytest.raises(ValueError):
        hi_penalizado(4000, 10000, 0.6, p)                                                  # falta ks_prom_antesis


def test_hi_acepta_arreglos_y_rechaza_opcion_invalida(params):
    p = _con(params, lue__hi_opcion="A")
    out = hi_penalizado(np.array([1, 2]), np.array([10, 10]), np.array([1.0, 0.5]), p)
    assert out.shape == (2,) and out[0] > out[1]
    with pytest.raises(ValueError):
        hi_penalizado(1, 2, 0.5, _con(params, lue__hi_opcion="Z"))
