"""
Carga de datos según docs/CONTRATO_DE_DATOS.md. TODOS los módulos reciben el DataFrame que
devuelve cargar_entrada(); nadie debería leer los CSV por su cuenta.
"""
from pathlib import Path

import pandas as pd
import yaml

RENOMBRAR_CLIMA = {
    "temperature_2m_max": "tmax",
    "temperature_2m_min": "tmin",
    "precipitation_sum": "pcp",
    "shortwave_radiation_sum": "rs",
    "et0_fao_evapotranspiration": "eto_om",
}
COLS_FECHA_BASE = ["fecha_siembra", "fecha_siembra_A", "fecha_siembra_B", "fecha_sos", "fecha_pico"]


def cargar_params(raiz="."):
    """Lee configs/params.yaml. Los parámetros NUNCA se escriben dentro del código."""
    with open(Path(raiz) / "configs/params.yaml") as f:
        return yaml.safe_load(f)


def cargar_entrada(raiz="."):
    """Devuelve (diario, base).
    diario: una fila por parcela y día (ID_POLIGON, fecha, tmax, tmin, pcp, rs, eto_om,
            fapar_final, fapar_s2, ndvi_planet) + todas las columnas de parcelas_base.
    base:   parcelas_base.csv (una fila por parcela)."""
    r = Path(raiz)
    clima = pd.read_csv(r / "data/external/clima_diario_parcelas_2025.csv", parse_dates=["fecha"])
    clima = clima.rename(columns=RENOMBRAR_CLIMA)[
        ["ID_POLIGON", "fecha", "tmax", "tmin", "pcp", "rs", "eto_om"]]
    sat = pd.read_csv(r / "data/processed/series_satelite_diarias_2025.csv", parse_dates=["fecha"])
    sat = sat[["ID_POLIGON", "fecha", "fapar_final", "fapar_s2", "ndvi_planet"]]
    base = pd.read_csv(r / "data/processed/parcelas_base.csv", parse_dates=COLS_FECHA_BASE)

    diario = (clima.merge(sat, on=["ID_POLIGON", "fecha"], how="left", validate="1:1")
                   .merge(base, on="ID_POLIGON", how="left", validate="m:1"))
    diario = diario.sort_values(["ID_POLIGON", "fecha"]).reset_index(drop=True)
    return diario, base
