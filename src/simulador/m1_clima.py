"""Módulo 1: clima diario derivado. Ver docs/GUIA_DE_MODULOS.md (sección M1)."""
import pandas as pd


def m1_clima(df_in: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Agrega las columnas: tmean, ra, par, eto.
    - tmean = (tmax + tmin) / 2                                      [°C]
    - ra    = radiación extraterrestre, FAO-56 ec. 21 (lat, día del año) [MJ/m2/día]
    - par   = params['cultivo']['par_fraccion'] * rs                 [MJ/m2/día]
    - eto   = Hargreaves-Samani (ra convertida a mm/día: x 0.408)    [mm/día]
    No modifica las columnas de entrada. Devuelve un DataFrame nuevo."""
    raise NotImplementedError("M1 pendiente")
