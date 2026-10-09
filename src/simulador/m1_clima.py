"""Módulo 1: clima diario derivado. Ver docs/GUIA_DE_MODULOS.md (sección 5)."""
import numpy as np
import pandas as pd

GSC = 0.0820          # constante solar, MJ/m2/min (FAO-56)
LAMBDA_INV = 0.408    # MJ/m2/día -> mm/día de evaporación equivalente (FAO-56)
COLS_REQUERIDAS = ["fecha", "lat", "tmax", "tmin", "rs"]


def radiacion_extraterrestre(lat_deg, doy):
    """Ra [MJ/m2/día], FAO-56 ecuación 21. lat_deg y doy pueden ser escalares o arreglos."""
    phi = np.deg2rad(np.asarray(lat_deg, dtype=float))
    doy = np.asarray(doy, dtype=float)
    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi * doy / 365.0)
    delta = 0.409 * np.sin(2.0 * np.pi * doy / 365.0 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0))
    ra = (24.0 * 60.0 / np.pi) * GSC * dr * (
        ws * np.sin(phi) * np.sin(delta) + np.cos(phi) * np.cos(delta) * np.sin(ws))
    return np.maximum(ra, 0.0)


def m1_clima(df_in: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Agrega las columnas: tmean, ra, par, eto.
    - tmean = (tmax + tmin) / 2                                          [°C]
    - ra    = radiación extraterrestre, FAO-56 ec. 21 (lat, día del año) [MJ/m2/día]
    - par   = params['cultivo']['par_fraccion'] * rs                     [MJ/m2/día]
    - eto   = Hargreaves-Samani, FAO-56 ec. 52 (ra convertida a mm/día: x 0.408) [mm/día]
              eto = factor * 0.0023 * (tmean + 17.8) * sqrt(tmax - tmin) * ra * 0.408
    El factor de corrección sale de params['clima']['factor_eto'] (1.0 si no existe: sin corrección;
    ver decisión abierta 3 del contrato).
    No modifica las columnas de entrada. Devuelve un DataFrame nuevo.
    Los vacíos no se rellenan aquí: la limpieza de datos no es tarea de un módulo."""
    faltan = [c for c in COLS_REQUERIDAS if c not in df_in.columns]
    if faltan:
        raise KeyError(f"M1 requiere las columnas {faltan}")
    for c in ["tmax", "tmin", "rs", "lat"]:
        if df_in[c].isna().any():
            raise ValueError(f"M1: la columna '{c}' tiene valores vacíos")

    par_fraccion = float(params["cultivo"]["par_fraccion"])
    factor_eto = float(params.get("clima", {}).get("factor_eto", 1.0))
    if factor_eto <= 0:
        raise ValueError(f"clima.factor_eto debe ser positivo, se recibió {factor_eto}")

    df = df_in.copy()
    tmax = df["tmax"].astype(float)
    tmin = df["tmin"].astype(float)
    doy = pd.to_datetime(df["fecha"]).dt.dayofyear.to_numpy()

    df["tmean"] = (tmax + tmin) / 2.0
    df["par"] = par_fraccion * df["rs"].astype(float)
    df["ra"] = radiacion_extraterrestre(df["lat"].to_numpy(float), doy)

    rango = np.sqrt(np.maximum(0.0, tmax - tmin))
    eto = factor_eto * 0.0023 * (df["tmean"] + 17.8) * rango * (df["ra"] * LAMBDA_INV)
    df["eto"] = np.maximum(eto, 0.0)
    return df


def razon_eto_mensual(df: pd.DataFrame) -> pd.Series:
    """Validación (guía, sección 5): cociente medio mensual eto / eto_om (Penman-Monteith de Open-Meteo).
    Requiere las columnas eto (M1) y eto_om. Devuelve una serie indexada por mes."""
    d = df[["fecha", "eto", "eto_om"]].copy()
    d["mes"] = pd.to_datetime(d["fecha"]).dt.month
    g = d.groupby("mes")[["eto", "eto_om"]].sum()
    return (g["eto"] / g["eto_om"]).rename("razon_eto_sobre_eto_om")
