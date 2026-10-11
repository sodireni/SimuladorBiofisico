"""Pruebas de las 12 variables (guía, sección 9) con un caso hecho a mano: tmean = 10 °C constante, Tbase 0."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from simulador.io import cargar_params
from simulador.m2_fenologia import m2_fenologia
from simulador.m3_balance_hidrico import m3_balance_hidrico
from simulador.m4_lue import m4_lue
from simulador.variables import EXTRAS, VARIABLES_12, calcular_variables, exportar_entregable, exportar_extras

RAIZ = str(Path(__file__).resolve().parents[1])
SIEMBRA = pd.Timestamp("2025-04-01")


@pytest.fixture
def params():
    p = cargar_params(RAIZ)
    p["fenologia"].update(tbase_c=0.0, modo="umbral_gdd")
    p["cultivo"].update(rue_max_g_mj_par=2.5, hi_base=0.45)
    p["lue"].update(hi_opcion="C", hi_sens_antesis=0.5, hi_sens_llenado=0.3)
    p["suelo"]["sw_inicial_frac_awc"] = 1.0
    p["clima"] = {"factor_eto": 1.0}
    return p


def _parcela(id_="AGC_001", pico_dias=90, n=220, pcp=20.0, fapar=0.5):
    f = pd.date_range("2025-03-15", periods=n)
    return pd.DataFrame({
        "ID_POLIGON": id_, "fecha": f, "tmean": 10.0, "pcp": pcp, "eto": 4.0, "par": 10.0, "fapar_final": fapar,
        "fecha_siembra": SIEMBRA, "fecha_pico": SIEMBRA + pd.Timedelta(days=pico_dias),
        "FC_mm": 154.0, "PWP_mm": 92.0, "AWC_mm": 62.0})


def _simular(df, params):
    return m4_lue(m3_balance_hidrico(m2_fenologia(df, params), params), params)


def test_valores_a_mano(params):
    params["fenologia"]["gdd_variables_ref"] = "pico_ndvi_hasta_madurez_modelo"
    # Con 10 °C·d/día: antesis a los 79 días (800 °C·d) y madurez a los 144 (1450 °C·d); el ciclo dura 145 días.
    v = calcular_variables(_simular(_parcela(pico_dias=90), params), None, params).iloc[0]
    assert v["GDD_antesis"] == pytest.approx(910.0)                 # pico a los 90 días: 91 días x 10
    assert v["GDD_llenado"] == pytest.approx(1450.0 - 910.0)
    assert v["DAP_antesis_est"] == 79
    assert v["ETo_acum"] == pytest.approx(4.0 * 145)
    assert v["Deficit_Hidrico_Total"] == pytest.approx(v["ETo_acum"] - v["ETa_acum"])
    assert v["Deficit_ETc"] == pytest.approx(0.0, abs=1e-9)         # sin estrés: ETa = ETc
    assert v["Deficit_Hidrico_Total"] > 0                            # pero ETo - ETa mide el efecto de Kc
    assert v["KS_prom_antesis"] == 1.0 and v["KS_prom_llenado"] == 1.0
    assert v["fPAR_integrado"] == pytest.approx(0.5 * 145)
    assert v["Biomasa_Total_Sim"] == pytest.approx(145 * 125.0)     # 10 * 0.5 * 2.5 * 1 * 10 = 125 kg/ha/día
    assert v["Biomasa_Antesis_Sim"] == pytest.approx(80 * 125.0)    # día 0 a día 79
    assert v["HI_penalizado"] == pytest.approx(0.45)
    assert bool(v["ciclo_incompleto"]) is False


def test_referencia_antesis_da_la_definicion_de_la_guia(params):
    params["fenologia"]["gdd_variables_ref"] = "antesis"
    v = calcular_variables(_simular(_parcela(pico_dias=90), params), None, params).iloc[0]
    assert v["GDD_antesis"] == pytest.approx(800.0) and v["GDD_llenado"] == pytest.approx(650.0)


def test_llenado_hasta_madurez_del_modelo_nunca_es_negativo(params):
    params["fenologia"]["gdd_variables_ref"] = "pico_ndvi_hasta_madurez_modelo"
    d = pd.concat([_parcela("AGC_001", pico_dias=60), _parcela("AGC_002", pico_dias=100), _parcela("AGC_003", pico_dias=150)])
    v = calcular_variables(_simular(d, params), None, params).set_index("ID_POLIGON")
    assert v["GDD_antesis"].tolist() == pytest.approx([610.0, 1010.0, 1510.0])
    assert v["GDD_llenado"].tolist() == pytest.approx([840.0, 440.0, 0.0])        # pico después de la madurez: 0, no negativo


def _fapar_con_caida(pico_dias, n=220, valor_pico=0.8, caida_por_dia=0.01):
    k = (pd.date_range("2025-03-15", periods=n) - SIEMBRA).days.to_numpy()
    f = np.where(k <= pico_dias, valor_pico * np.clip(k, 0, None) / pico_dias, valor_pico - caida_por_dia * (k - pico_dias))
    return np.clip(f, 0.0, None)


def test_llenado_del_pico_a_la_caida_del_fpar(params):
    # pico a los 90 días (0.8); cae 0.01/día -> llega a 0.4 (la mitad) 40 días después, en k = 130
    # gdd(k=130) = 131 días x 10 = 1310; gdd(pico, k=90) = 910 -> GDD_llenado = 400
    v = calcular_variables(_simular(_parcela(pico_dias=90, fapar=_fapar_con_caida(90)), params), None, params).iloc[0]
    assert v["GDD_antesis"] == pytest.approx(910.0)
    assert v["GDD_llenado"] == pytest.approx(400.0)
    assert bool(v["caida_fpar_no_alcanzada"]) is False


def test_llenado_por_caida_no_es_cero_aunque_el_pico_pase_la_madurez(params):
    # pico a los 150 días: la madurez por umbral (k=144) ya pasó, pero la caída del fPAR sí ocurre después del pico
    v = calcular_variables(_simular(_parcela(pico_dias=150, fapar=_fapar_con_caida(150)), params), None, params).iloc[0]
    assert v["GDD_antesis"] == pytest.approx(1510.0)
    assert v["GDD_llenado"] == pytest.approx(400.0) and v["GDD_llenado"] > 0


def test_si_el_fpar_no_cae_se_marca_y_usa_el_ultimo_dia(params):
    v = calcular_variables(_simular(_parcela(pico_dias=90, fapar=0.5), params), None, params).iloc[0]   # fPAR constante
    assert bool(v["caida_fpar_no_alcanzada"]) is True
    assert v["GDD_llenado"] == pytest.approx(2030.0 - 910.0)           # 203 días de cultivo x 10 = 2030 en el último día


def test_ciclo_incompleto_se_marca(params):
    v = calcular_variables(_simular(_parcela(pico_dias=40, n=90), params), None, params).iloc[0]
    assert bool(v["ciclo_incompleto"]) is True


def test_errores_claros(params):
    sim = _simular(_parcela(), params)
    with pytest.raises(KeyError):
        calcular_variables(sim.drop(columns=["bio"]), None, params)
    malo = {**params, "fenologia": {**params["fenologia"], "gdd_variables_ref": "otro"}}
    with pytest.raises(ValueError):
        calcular_variables(sim, None, malo)


def test_exporta_entregable_y_extras(params, tmp_path):
    d = pd.concat([_parcela("AGC_001"), _parcela("AGC_002", pico_dias=100)])
    v = calcular_variables(_simular(d, params), None, params)
    assert list(v.columns) == ["ID_POLIGON", *VARIABLES_12, *EXTRAS]
    out = exportar_entregable(v, str(tmp_path / "bio.csv"))
    assert list(out.columns) == ["ID_parcela", *VARIABLES_12] and len(out) == 2
    ex = exportar_extras(v, str(tmp_path / "extras.csv"))
    assert list(ex.columns) == ["ID_parcela", *EXTRAS]


def test_rangos_con_datos_sinteticos(entrada, params):
    from simulador.m1_clima import m1_clima
    p = cargar_params(RAIZ)
    sim = m4_lue(m3_balance_hidrico(m2_fenologia(m1_clima(entrada, p), p), p), p)
    v = calcular_variables(sim, None, p)
    assert len(v) == 3 and v[VARIABLES_12].notna().all().all()
    assert (v["Deficit_Hidrico_Total"] >= 0).all() and (v["Deficit_ETc"] >= -1e-9).all()
    assert v["KS_prom_antesis"].between(0, 1).all() and v["KS_prom_llenado"].between(0, 1).all()
    assert (v["HI_penalizado"] <= p["cultivo"]["hi_base"] + 1e-12).all()
    assert (v["Biomasa_Antesis_Sim"] <= v["Biomasa_Total_Sim"]).all()
