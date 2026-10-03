"""
Extrae elevación y pendiente por parcela (media dentro del polígono).

Fuente: INEGI, Continuo de Elevaciones Mexicano 4.0 (CEM 4.0), entregado por el reto
a 120 m. La pendiente viene en GRADOS; aquí se agrega también en % (= tan(grados)*100).

Uso (desde la carpeta principal del proyecto):
    python src/ingest/extraer_topografia.py

Salida:
    data/processed/topografia_parcelas.csv
"""
import os

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask

SHP = "data/raw/Parcelas_Reto_AGC_CONJUNTO.shp"
BASE = "data/raw/Reto_AgroCebada_Topografia_INEGI_CEM4/Reto_AgroCebada_Topografia_INEGI_CEM4/"
ELEV = BASE + "Elevacion_INEGI_CEM4_120m.tif"
PEND = BASE + "Pendiente_INEGI_CEM4_120m_grados.tif"
CLIMA = "data/external/clima_diario_parcelas_2025.csv"   # solo para un chequeo cruzado
SALIDA = "data/processed/topografia_parcelas.csv"


def media_por_poligono(ruta_raster, gdf):
    """Media del raster dentro de cada polígono. Si el polígono es más chico que un
    píxel (120 m) y no toca ninguno, usa el píxel del centroide. Devuelve (valores, n_respaldo)."""
    g = gdf.to_crs(rasterio.open(ruta_raster).crs)
    out, respaldo = [], 0
    with rasterio.open(ruta_raster) as src:
        for geom in g.geometry:
            val = np.nan
            try:
                arr, _ = mask(src, [geom], crop=True, all_touched=True, filled=False)
                datos = arr[0].compressed().astype(float)
                if src.nodata is not None:
                    datos = datos[datos != src.nodata]
                if datos.size:
                    val = datos.mean()
            except ValueError:      # el polígono no se cruza con el raster
                pass
            if np.isnan(val):
                c = geom.centroid
                v = next(src.sample([(c.x, c.y)]))[0]
                val = np.nan if (src.nodata is not None and v == src.nodata) else float(v)
                respaldo += 1
            out.append(val)
    return np.array(out), respaldo


def main():
    gdf = gpd.read_file(SHP)
    print("Columnas del shapefile:", list(gdf.columns))
    print("CRS del shapefile:", gdf.crs)

    # Columna de ID: la primera cuyo contenido empiece con "AGC_"
    col_id = next(c for c in gdf.columns
                  if gdf[c].astype(str).str.startswith("AGC_").all())
    print("Columna de ID detectada:", col_id)

    elev, r1 = media_por_poligono(ELEV, gdf)
    pend_deg, r2 = media_por_poligono(PEND, gdf)
    print(f"Parcelas que usaron el píxel del centroide: elevación={r1}, pendiente={r2}")

    df = pd.DataFrame({
        "ID_POLIGON": gdf[col_id].values,
        "elev_m": elev.round(1),
        "pendiente_deg": pend_deg.round(2),
        "pendiente_pct": (np.tan(np.radians(pend_deg)) * 100).round(2),
    })
    if "CONJUNTO" in gdf.columns:
        df["CONJUNTO"] = gdf["CONJUNTO"].values

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    df.to_csv(SALIDA, index=False)

    print("\nParcelas:", len(df), "| Nulos:", int(df[['elev_m', 'pendiente_deg']].isna().sum().sum()))
    print(df[["elev_m", "pendiente_deg", "pendiente_pct"]].describe().round(1).to_string())

    # Chequeo cruzado: la elevación que usó Open-Meteo debe parecerse a la del INEGI
    if os.path.exists(CLIMA):
        om = (pd.read_csv(CLIMA).groupby("ID_POLIGON")["elevacion_modelo_m"].first()
              .rename("elev_openmeteo_m"))
        cmp = df.merge(om, on="ID_POLIGON")
        dif = cmp["elev_m"] - cmp["elev_openmeteo_m"]
        print(f"\nElevación INEGI vs Open-Meteo: correlación={cmp['elev_m'].corr(cmp['elev_openmeteo_m']):.2f}, "
              f"diferencia media={dif.mean():.0f} m, máxima absoluta={dif.abs().max():.0f} m")


if __name__ == "__main__":
    main()
