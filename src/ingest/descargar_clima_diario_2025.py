"""
Descarga clima DIARIO del ciclo 2025 para cada parcela (insumo del Módulo 1).

Fuente: Open-Meteo Historical Weather API (reanálisis ERA5 / ERA5-Land).
Cada parcela se consulta con sus coordenadas EXACTAS, porque Open-Meteo ajusta
la temperatura por la altitud del punto y eso conserva la variación entre parcelas.

Cita sugerida (docs/FUENTES.md):
  - Zippenfenig, P. (2023). Open-Meteo.com Weather API. Zenodo (CC BY 4.0).
  - Hersbach, H. et al. (2020). The ERA5 global reanalysis. QJRMS, 146.
  - Muñoz-Sabater, J. et al. (2021). ERA5-Land. Earth Syst. Sci. Data, 13.

Uso (desde la carpeta principal del proyecto):
    python src/ingest/descargar_clima_diario_2025.py

Si se interrumpe, vuelve a correrlo: omite las parcelas ya descargadas
(guardadas en data/external/cache_clima/).

Salida:
    data/external/clima_diario_parcelas_2025.csv   (una fila por parcela y día)
"""
import os
import time

import pandas as pd
import requests

COORDS_CSV = "data/processed/coordenadas_parcelas.csv"  # ID_POLIGON, latitud, longitud
OUT_DIR = "data/external"
CACHE_DIR = f"{OUT_DIR}/cache_clima"
INICIO, FIN = "2025-03-15", "2025-10-31"
URL = "https://archive-api.open-meteo.com/v1/archive"
VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "shortwave_radiation_sum",        # MJ/m2/día
    "et0_fao_evapotranspiration",     # solo para comparar con tu ETo Hargreaves
]


def pedir(lat, lon, reintentos=6):
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": INICIO,
        "end_date": FIN,
        "daily": ",".join(VARIABLES),
        "timezone": "America/Mexico_City",
    }
    for i in range(reintentos):
        r = requests.get(URL, params=params, timeout=60)
        if r.status_code == 200:
            js = r.json()
            return pd.DataFrame(js["daily"]), js.get("elevation")
        if r.status_code == 429:
            espera = 30 * (i + 1)
            print(f"  límite de uso, esperando {espera}s...")
            time.sleep(espera)
            continue
        r.raise_for_status()
    raise RuntimeError(f"No se pudo descargar {lat},{lon}")


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    par = pd.read_csv(COORDS_CSV)
    total = len(par)
    print(f"{total} parcelas a descargar (una consulta por parcela)")

    for k, p in enumerate(par.itertuples(index=False), 1):
        ruta = f"{CACHE_DIR}/{p.ID_POLIGON}.csv"
        if os.path.exists(ruta):
            continue
        if k % 10 == 0 or k == total:
            print(f"[{k}/{total}] {p.ID_POLIGON}")
        df, elev = pedir(p.latitud, p.longitud)
        df = df.rename(columns={"time": "fecha"})
        df.insert(0, "ID_POLIGON", p.ID_POLIGON)
        df["elevacion_modelo_m"] = elev
        df.to_csv(ruta, index=False)
        time.sleep(0.5)

    todo = pd.concat(
        [pd.read_csv(f"{CACHE_DIR}/{i}.csv") for i in par["ID_POLIGON"]],
        ignore_index=True,
    )
    todo = par.merge(todo, on="ID_POLIGON", how="left")
    todo.to_csv(f"{OUT_DIR}/clima_diario_parcelas_2025.csv", index=False)

    print("\nNulos por variable:\n", todo[VARIABLES].isna().sum().to_string())
    print("Filas:", len(todo), "| Parcelas:", todo["ID_POLIGON"].nunique())
    print("Series distintas (Tmax,lluvia):",
          todo.groupby("ID_POLIGON")[["temperature_2m_max", "precipitation_sum"]]
          .sum().round(1).drop_duplicates().shape[0])


if __name__ == "__main__":
    main()
