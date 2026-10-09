"""Pruebas de la carga de datos y del entregable (sí deben pasar desde hoy)."""
import pandas as pd
import pytest

from simulador.io import RENOMBRAR_CLIMA, cargar_entrada
from simulador.variables import VARIABLES_12, exportar_entregable

from conftest import VENTANA, entrada_sintetica


def test_hay_12_variables_sin_repetidos():
    assert len(VARIABLES_12) == 12 and len(set(VARIABLES_12)) == 12


def test_cargar_entrada_une_bien(tmp_path):
    d = entrada_sintetica(n_parcelas=2)
    (tmp_path / "data/external").mkdir(parents=True)
    (tmp_path / "data/processed").mkdir(parents=True)
    inv = {v: k for k, v in RENOMBRAR_CLIMA.items()}
    clima = d[["ID_POLIGON", "fecha", "tmax", "tmin", "pcp", "rs", "eto_om"]].rename(columns=inv)
    clima.to_csv(tmp_path / "data/external/clima_diario_parcelas_2025.csv", index=False)
    d[["ID_POLIGON", "fecha", "fapar_final", "fapar_s2", "ndvi_planet"]].to_csv(
        tmp_path / "data/processed/series_satelite_diarias_2025.csv", index=False)
    base = d.drop_duplicates("ID_POLIGON").drop(
        columns=["fecha", "tmax", "tmin", "pcp", "rs", "eto_om", "fapar_final", "fapar_s2", "ndvi_planet"])
    base["fecha_sos"] = base["fecha_pico"]
    base.to_csv(tmp_path / "data/processed/parcelas_base.csv", index=False)

    diario, b = cargar_entrada(str(tmp_path))
    assert len(diario) == 2 * len(VENTANA) and len(b) == 2
    assert diario["fecha_siembra"].dtype.kind == "M"
    assert not diario[["tmax", "pcp", "fapar_final", "FC_mm"]].isna().any().any()


def test_entregable_valida_y_renombra(tmp_path):
    v = pd.DataFrame({"ID_POLIGON": ["AGC_001", "AGC_002"], **{c: [1.0, 2.0] for c in VARIABLES_12}})
    out = exportar_entregable(v, str(tmp_path / "x.csv"))
    assert list(out.columns) == ["ID_parcela", *VARIABLES_12]
    with pytest.raises(ValueError):
        exportar_entregable(v.drop(columns=["ETo_acum"]), str(tmp_path / "y.csv"))
    with pytest.raises(ValueError):
        w = v.copy(); w.loc[0, "ETa_acum"] = float("nan")
        exportar_entregable(w, str(tmp_path / "z.csv"))
