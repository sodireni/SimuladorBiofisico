"""
Control de calidad: lluvia mensual de Open-Meteo (suma de la serie diaria)
contra el CHIRPS mensual 2025 que entrega el reto, en el centroide de cada parcela.

Uso (desde la carpeta principal del proyecto):
    python src/ingest/qc_clima_vs_chirps.py

Solo compara abril-octubre: marzo está incompleto en la descarga (inicia el 15).
"""
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

CLIMA = "data/external/clima_diario_parcelas_2025.csv"
COORDS = "data/processed/coordenadas_parcelas.csv"
CHIRPS = ("data/raw/Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025/"
          "Precipitacion_mensual/2025/PREC_2025_{mes:02d}.tif")

clima = pd.read_csv(CLIMA)
clima["mes"] = clima["fecha"].str[5:7].astype(int)
om = (clima.groupby(["ID_POLIGON", "mes"])["precipitation_sum"]
      .sum().rename("om_mm").reset_index())

pts = pd.read_csv(COORDS)
gdf = gpd.GeoDataFrame(pts, geometry=gpd.points_from_xy(pts["longitud"], pts["latitud"]),
                       crs="EPSG:4326")

filas = []
for mes in range(4, 11):
    with rasterio.open(CHIRPS.format(mes=mes)) as src:
        g = gdf.to_crs(src.crs)
        vals = [v[0] for v in src.sample(zip(g.geometry.x, g.geometry.y))]
        vals = np.array(vals, dtype=float)
        if src.nodata is not None:
            vals[vals == src.nodata] = np.nan
    ch = pd.DataFrame({"ID_POLIGON": gdf["ID_POLIGON"], "mes": mes, "chirps_mm": vals})
    filas.append(ch)

cmp = om.merge(pd.concat(filas), on=["ID_POLIGON", "mes"])

res = cmp.groupby("mes").apply(lambda x: pd.Series({
    "OpenMeteo_mm": x["om_mm"].mean(),
    "CHIRPS_mm": x["chirps_mm"].mean(),
    "razon_OM/CHIRPS": x["om_mm"].mean() / x["chirps_mm"].mean(),
    "corr_entre_parcelas": x["om_mm"].corr(x["chirps_mm"]),
}), include_groups=False).round(2)
print(res.to_string())

tot = cmp.groupby("ID_POLIGON")[["om_mm", "chirps_mm"]].sum()
print("\nTotal abril-octubre (promedio de parcelas): "
      f"OpenMeteo={tot.om_mm.mean():.0f} mm | CHIRPS={tot.chirps_mm.mean():.0f} mm")
print(f"Correlación entre parcelas (total): {tot.om_mm.corr(tot.chirps_mm):.2f}")
print("Valores CHIRPS nulos:", int(cmp['chirps_mm'].isna().sum()))
