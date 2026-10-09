"""
Datos sintéticos que respetan docs/CONTRATO_DE_DATOS.md, para probar cada módulo SIN depender de
que los demás estén terminados ni de los archivos reales.

  entrada_sintetica()    -> lo que devuelve cargar_entrada() (clima + satélite + parcelas_base)
  con_m1_m2(df)          -> le agrega columnas plausibles de M1 y M2 (para trabajar en M3 y M4)
  con_m3(df)             -> le agrega ks y eta plausibles (para trabajar en M4)
"""
import numpy as np
import pandas as pd
import pytest

VENTANA = pd.date_range("2025-03-15", "2025-11-30")      # 261 días


def entrada_sintetica(n_parcelas=3, semilla=0):
    rng = np.random.default_rng(semilla)
    filas = []
    for i in range(n_parcelas):
        n = len(VENTANA)
        doy = VENTANA.dayofyear.to_numpy()
        tmax = 22 - 3 * np.cos((doy - 150) / 365 * 2 * np.pi) + rng.normal(0, 1.5, n)
        tmin = tmax - 13 + rng.normal(0, 1, n)
        llueve = (rng.random(n) < np.where((doy > 150) & (doy < 290), 0.55, 0.1))
        pcp = np.where(llueve, rng.gamma(1.2, 7, n), 0.0)
        siembra = pd.Timestamp("2025-05-30") + pd.Timedelta(days=int(rng.integers(0, 20)))
        pico = pd.Timestamp("2025-09-01") + pd.Timedelta(days=int(rng.integers(-10, 20)))
        x = (VENTANA - siembra).days.to_numpy()
        fapar = np.clip(0.08 + 0.6 * np.exp(-((VENTANA - pico).days.to_numpy() / 45.0) ** 2), 0, 0.95)
        filas.append(pd.DataFrame({
            "ID_POLIGON": f"AGC_{i + 1:03d}", "fecha": VENTANA,
            "tmax": tmax, "tmin": tmin, "pcp": pcp, "rs": np.clip(rng.normal(23, 4, n), 5, 31),
            "eto_om": np.clip(rng.normal(4.1, 1.0, n), 0.7, 6.7),
            "fapar_final": fapar, "fapar_s2": fapar, "ndvi_planet": fapar + 0.1,
            "lat": 19.7, "lon": -98.4, "elev_m": 2650.0, "pendiente_pct": 3.0,
            "fecha_siembra": siembra, "fecha_siembra_A": siembra, "fecha_siembra_B": siembra,
            "doble_ciclo": False, "fecha_pico": pico, "ndvi_pico": 0.75,
            "FC_mm": 154.0, "PWP_mm": 92.0, "AWC_mm": 62.0, "AWC_mm_sin_grava": 77.0,
        }))
    return pd.concat(filas, ignore_index=True)


def con_m1_m2(df):
    """Columnas plausibles de M1 y M2 (NO son los cálculos reales: sirven para desarrollar M3/M4)."""
    d = df.copy()
    d["tmean"] = (d["tmax"] + d["tmin"]) / 2
    d["ra"] = 38.0
    d["par"] = 0.48 * d["rs"]
    d["eto"] = d["eto_om"]
    gdd = np.where(d["fecha"] >= d["fecha_siembra"], np.maximum(0, d["tmean"]), 0.0)
    d["gdd_acum"] = pd.Series(gdd).groupby(d["ID_POLIGON"]).cumsum().to_numpy()
    d["fecha_antesis"] = d["fecha_pico"]
    d["fecha_madurez"] = d["fecha_pico"] + pd.Timedelta(days=60)
    dias = (d["fecha"] - d["fecha_antesis"]).dt.days
    d["estadio"] = np.select(
        [d["fecha"] < d["fecha_siembra"], dias.abs() <= 10, dias < 0, d["fecha"] <= d["fecha_madurez"]],
        ["pre_siembra", "antesis", "vegetativo", "llenado"], default="madurez")
    d["kc"] = np.select([d["estadio"] == "pre_siembra", d["estadio"] == "vegetativo",
                         d["estadio"].isin(["antesis", "llenado"])], [0.30, 0.70, 1.15], default=0.25)
    return d


def con_m3(df):
    d = df.copy()
    d["ks"] = 1.0
    d["eta"] = d["eto"] * d["kc"] * d["ks"]
    d["sw"] = d["PWP_mm"] + 0.5 * d["AWC_mm"]
    return d


@pytest.fixture
def entrada():
    return entrada_sintetica()


@pytest.fixture
def entrada_m1_m2():
    return con_m1_m2(entrada_sintetica())


@pytest.fixture
def entrada_m3():
    return con_m3(con_m1_m2(entrada_sintetica()))
