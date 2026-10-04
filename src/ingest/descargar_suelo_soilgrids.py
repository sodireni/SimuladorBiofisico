"""
Descarga capas de SoilGrids 2.0 (ISRIC) por WCS, en el rectángulo que cubre todas las parcelas.

Por qué WCS: la API REST de SoilGrids está pausada por ISRIC (sin fecha de regreso) y además es
beta y limitada a 5 llamadas/min. WCS es la ruta que ISRIC recomienda para obtener recortes.

Descarga, para 4 profundidades (0-5, 5-15, 15-30, 30-60 cm), la predicción media ("mean") de:
  clay, sand, silt  (g/kg)      -> dividir entre 10 para obtener %
  bdod              (cg/cm3)    -> dividir entre 100 para obtener g/cm3
  soc               (dg/kg)     -> dividir entre 10 para obtener g/kg
  cfvo              (cm3/dm3)   -> fragmentos gruesos; dividir entre 10 para obtener %
(Verifica las unidades en la metadata de cada capa antes de convertir.)

Cita (docs/FUENTES.md): Poggio, L. et al. (2021). SoilGrids 2.0: producing soil information for the
globe with quantified spatial uncertainty. SOIL, 7, 217-240. https://doi.org/10.5194/soil-7-217-2021
Licencia de los datos: CC BY 4.0. Servicio WCS: https://maps.isric.org

Uso (desde la carpeta principal del proyecto):
    python src/ingest/descargar_suelo_soilgrids.py

Si se interrumpe, vuelve a correrlo: omite lo ya descargado.
Salida: data/external/soilgrids/<propiedad>_<profundidad>_mean.tif
"""
import os
import time

import pandas as pd
import requests

COORDS = "data/processed/coordenadas_parcelas.csv"
OUT = "data/external/soilgrids"
URL = "https://maps.isric.org/mapserv"
PROPIEDADES = ["clay", "sand", "silt", "bdod", "soc", "cfvo"]
PROFUNDIDADES = ["0-5cm", "5-15cm", "15-30cm", "30-60cm"]
MARGEN = 0.05          # grados de margen alrededor de las parcelas
REINTENTOS = 5
TIMEOUT = 240
EPSG4326 = "http://www.opengis.net/def/crs/EPSG/0/4326"


def es_tiff(b):
    return b[:4] in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")


def descargar(prop, prof, bbox, ruta):
    west, south, east, north = bbox
    params = [
        ("map", f"/map/{prop}.map"),
        ("SERVICE", "WCS"),
        ("VERSION", "2.0.1"),
        ("REQUEST", "GetCoverage"),
        ("COVERAGEID", f"{prop}_{prof}_mean"),
        ("FORMAT", "image/tiff"),
        ("SUBSET", f"long({west:.4f},{east:.4f})"),
        ("SUBSET", f"lat({south:.4f},{north:.4f})"),
        ("SUBSETTINGCRS", EPSG4326),
        ("OUTPUTCRS", EPSG4326),
    ]
    for i in range(REINTENTOS):
        try:
            r = requests.get(URL, params=params, timeout=TIMEOUT)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            espera = 15 * (i + 1)
            print(f"   fallo de red ({type(e).__name__}); reintento {i + 1}/{REINTENTOS} en {espera}s")
            time.sleep(espera)
            continue
        if r.status_code == 200 and es_tiff(r.content):
            with open(ruta, "wb") as f:
                f.write(r.content)
            return True
        print(f"   respuesta inesperada (código {r.status_code}); inicio del contenido:")
        print("   ", r.content[:300].decode("utf-8", errors="replace").replace("\n", " "))
        if r.status_code in (400, 404):
            return False            # petición inválida: reintentar no ayuda
        espera = 15 * (i + 1)
        print(f"   reintento {i + 1}/{REINTENTOS} en {espera}s")
        time.sleep(espera)
    return False


def main():
    os.makedirs(OUT, exist_ok=True)
    c = pd.read_csv(COORDS)
    bbox = (c["longitud"].min() - MARGEN, c["latitud"].min() - MARGEN,
            c["longitud"].max() + MARGEN, c["latitud"].max() + MARGEN)
    print(f"Rectángulo (oeste, sur, este, norte): {tuple(round(v, 3) for v in bbox)}")

    total = len(PROPIEDADES) * len(PROFUNDIDADES)
    fallidas, k = [], 0
    for prop in PROPIEDADES:
        for prof in PROFUNDIDADES:
            k += 1
            ruta = f"{OUT}/{prop}_{prof}_mean.tif"
            if os.path.exists(ruta) and es_tiff(open(ruta, "rb").read(4)):
                continue
            print(f"[{k}/{total}] {prop} {prof}")
            if not descargar(prop, prof, bbox, ruta):
                fallidas.append(f"{prop}_{prof}")
            time.sleep(2)           # cortesía con el servidor

    print("\nDescargadas:", total - len(fallidas), "de", total)
    if fallidas:
        print("FALLARON:", fallidas, "\nVuelve a correr el script para reintentar solo esas.")

    try:                            # resumen rápido de lo descargado
        import rasterio
        print("\nResumen (valores crudos, sin convertir unidades):")
        for prop in PROPIEDADES:
            ruta = f"{OUT}/{prop}_0-5cm_mean.tif"
            if os.path.exists(ruta):
                with rasterio.open(ruta) as src:
                    a = src.read(1, masked=True)
                    print(f"  {prop:5s} 0-5cm: forma={src.shape} crs={src.crs} nodata={src.nodata} "
                          f"min={a.min():.0f} media={a.mean():.0f} max={a.max():.0f}")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
