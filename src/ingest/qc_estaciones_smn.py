"""
Compara Open-Meteo y CHIRTS-ERA5 (2025) contra las normales climatológicas del SMN en el punto
exacto de tres estaciones de Tlaxcala.

Datos de estación: SMN-CONAGUA, Normales Climatológicas (capturados a mano de las fichas por el
equipo). Temperaturas máxima y mínima NORMALES de abril a noviembre (°C).
  - Zoquiapan (29034) y Tocatlán (29027): confirmar el periodo de la normal en la ficha (se
    asume 1991-2020).
  - Hueyotlipan (29010): normal 1971-2000 (más antigua; probablemente más fría).

Limitaciones: una normal de 30 años no es el año 2025 (la variación interanual del promedio
mensual suele ser de ~1 °C); se promedian 8 meses y 3 estaciones para reducir ese ruido.
Para Open-Meteo se fuerza la altitud de la estación (parámetro 'elevation') para comparar en
igualdad de condiciones.

Uso (desde la carpeta principal del proyecto):
    python src/ingest/qc_estaciones_smn.py
"""
import time

import numpy as np
import pandas as pd
import requests

import qc_temperatura_vs_chirts as q

MESES = list(range(4, 12))     # abril-noviembre
ESTACIONES = {
    "Zoquiapan 29034": dict(lat=19.58472222, lon=-98.47805556, alt=2532,
                            tmax=[24.1, 24.4, 23.2, 22.1, 22.4, 21.9, 21.4, 21.1],
                            tmin=[5.2, 6.3, 7.3, 6.7, 6.6, 7.2, 5.2, 3.1]),
    "Tocatlan 29027": dict(lat=19.38861111, lon=-98.02138889, alt=2557,
                           tmax=[25.2, 24.9, 22.8, 21.9, 21.9, 21.0, 20.8, 20.5],
                           tmin=[8.4, 9.3, 9.8, 9.2, 9.2, 9.5, 7.8, 6.0]),
    "Hueyotlipan 29010": dict(lat=19.47194444, lon=-98.34527778, alt=2590,
                              tmax=[25.2, 25.4, 23.4, 22.2, 22.6, 22.3, 22.9, 22.9],
                              tmin=[5.0, 6.4, 7.9, 7.3, 7.2, 7.6, 5.8, 3.7]),
}
URL = "https://archive-api.open-meteo.com/v1/archive"


def pedir_open_meteo(lat, lon, alt, reintentos=6):
    params = {"latitude": lat, "longitude": lon, "elevation": alt,
              "start_date": "2025-04-01", "end_date": "2025-11-30",
              "daily": "temperature_2m_max,temperature_2m_min", "timezone": "America/Mexico_City"}
    for i in range(reintentos):
        try:
            r = requests.get(URL, params=params, timeout=90)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"  fallo de red ({type(e).__name__}); reintento {i + 1}/{reintentos}")
            time.sleep(10 * (i + 1))
            continue
        if r.status_code == 200:
            d = pd.DataFrame(r.json()["daily"])
            d["mes"] = pd.to_datetime(d["time"]).dt.month
            return d.groupby("mes")[["temperature_2m_max", "temperature_2m_min"]].mean()
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(30 * (i + 1))
            continue
        r.raise_for_status()
    raise RuntimeError("No se pudo descargar Open-Meteo para la estación")


def sesgos(tabla):
    """tabla: DataFrame con columnas normal_tmax, normal_tmin, om_tmax, om_tmin, ch_tmax, ch_tmin
    (una fila por estación y mes). Devuelve el sesgo medio (fuente - normal) de Tmax, Tmin, Tmean."""
    out = {}
    for fuente, pref in (("Open-Meteo", "om"), ("CHIRTS", "ch")):
        b_max = (tabla[f"{pref}_tmax"] - tabla["normal_tmax"]).mean()
        b_min = (tabla[f"{pref}_tmin"] - tabla["normal_tmin"]).mean()
        out[fuente] = {"Tmax": b_max, "Tmin": b_min, "Tmean": (b_max + b_min) / 2}
    return out


def main():
    filas = []
    for nombre, e in ESTACIONES.items():
        print(f"{nombre}: consultando Open-Meteo a {e['alt']} m ...")
        om = pedir_open_meteo(e["lat"], e["lon"], e["alt"]).reindex(MESES)
        pto = pd.DataFrame({"longitud": [e["lon"]], "latitud": [e["lat"]]})
        for k, mes in enumerate(MESES):
            filas.append({
                "estacion": nombre, "mes": mes,
                "normal_tmax": e["tmax"][k], "om_tmax": om.loc[mes, "temperature_2m_max"],
                "ch_tmax": float(q.muestrear_chirts("Tmax", mes, pto)[0]),
                "normal_tmin": e["tmin"][k], "om_tmin": om.loc[mes, "temperature_2m_min"],
                "ch_tmin": float(q.muestrear_chirts("Tmin", mes, pto)[0]),
            })
        time.sleep(2)
    t = pd.DataFrame(filas)
    pd.set_option("display.width", 200)
    print("\nDetalle por estación y mes (°C):")
    print(t.round(1).to_string(index=False))

    print("\nPor estación (promedio abril-noviembre):")
    for nombre, g in t.groupby("estacion"):
        s = sesgos(g)
        print(f"  {nombre:18s} sesgo Tmean: Open-Meteo {s['Open-Meteo']['Tmean']:+.1f} | "
              f"CHIRTS {s['CHIRTS']['Tmean']:+.1f}")
    s = sesgos(t)
    dias = len(pd.date_range("2025-04-01", "2025-11-30"))
    print("\nSesgo medio (fuente - normal del SMN), 3 estaciones, abril-noviembre:")
    for fuente, v in s.items():
        print(f"  {fuente:10s} Tmax {v['Tmax']:+.1f} | Tmin {v['Tmin']:+.1f} | Tmean {v['Tmean']:+.1f} °C"
              f"  -> efecto en grados-día ({dias} días): {v['Tmean'] * dias:+.0f} °C·d")


if __name__ == "__main__":
    main()
