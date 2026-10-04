"""
Control de calidad: Tmax y Tmin de Open-Meteo (promedio mensual de la serie diaria) contra los
rasters mensuales CHIRTS-ERA5 2025 que entrega el reto, en el centroide de cada parcela.

Compara abril-noviembre (meses completos dentro de la ventana de descarga).
Reporta, por mes: promedio de cada fuente, sesgo (Open-Meteo - CHIRTS), RMSE y correlación entre
parcelas. Al final estima cuánto cambiarían los grados-día acumulados por el sesgo de temperatura.

Uso (desde la carpeta principal del proyecto):
    python src/ingest/qc_temperatura_vs_chirts.py
"""
import numpy as np
import pandas as pd

CLIMA = "data/external/clima_diario_parcelas_2025.csv"
COORDS = "data/processed/coordenadas_parcelas.csv"
RUTA = "data/raw/Reto_AgroCebada_Temperatura_2022_2025/{var}/2025/{var}_2025_{mes:02d}.tif"
MESES = range(4, 12)
VARIABLES = {"Tmax": "temperature_2m_max", "Tmin": "temperature_2m_min"}


def muestrear_chirts(var, mes, coords):
    """Valor del raster CHIRTS (var, mes) en cada parcela. Devuelve un array (NaN si no hay dato)."""
    import geopandas as gpd
    import rasterio
    gdf = gpd.GeoDataFrame(coords, geometry=gpd.points_from_xy(coords["longitud"], coords["latitud"]),
                           crs="EPSG:4326")
    with rasterio.open(RUTA.format(var=var, mes=mes)) as src:
        g = gdf.to_crs(src.crs)
        v = np.array([x[0] for x in src.sample(zip(g.geometry.x, g.geometry.y))], dtype=float)
        if src.nodata is not None:
            v[v == src.nodata] = np.nan
    return v


def comparar(om, ch):
    """om, ch: arrays alineados por parcela. Devuelve un dict de métricas."""
    ok = ~(np.isnan(om) | np.isnan(ch))
    om, ch = om[ok], ch[ok]
    dif = om - ch
    return {"OpenMeteo": om.mean(), "CHIRTS": ch.mean(), "sesgo": dif.mean(),
            "RMSE": float(np.sqrt(np.mean(dif ** 2))),
            "corr_parcelas": float(np.corrcoef(om, ch)[0, 1]) if om.std() > 0 and ch.std() > 0 else np.nan,
            "n": int(ok.sum())}


def main():
    clima = pd.read_csv(CLIMA, parse_dates=["fecha"])
    clima["mes"] = clima["fecha"].dt.month
    coords = pd.read_csv(COORDS)
    ids = coords["ID_POLIGON"]

    sesgos = {}
    for var, col in VARIABLES.items():
        filas = []
        for mes in MESES:
            om = (clima[clima["mes"] == mes].groupby("ID_POLIGON")[col].mean()
                  .reindex(ids).to_numpy())
            ch = muestrear_chirts(var, mes, coords)
            if mes == MESES[0]:
                print(f"{var}: valores crudos de CHIRTS en {mes:02d}/2025 -> "
                      f"mín {np.nanmin(ch):.1f}, máx {np.nanmax(ch):.1f}  (deben estar en °C)")
            filas.append({"mes": mes, **comparar(om, ch)})
        t = pd.DataFrame(filas).set_index("mes").round(2)
        sesgos[var] = t["sesgo"].mean()
        print(f"\n{var}  (OpenMeteo vs CHIRTS-ERA5, °C)\n{t.to_string()}")

    sesgo_tmean = (sesgos["Tmax"] + sesgos["Tmin"]) / 2
    dias = len(pd.date_range("2025-04-01", "2025-11-30"))
    print(f"\nSesgo medio de Tmax: {sesgos['Tmax']:+.2f} °C | de Tmin: {sesgos['Tmin']:+.2f} °C "
          f"| de Tmean: {sesgo_tmean:+.2f} °C")
    print(f"Efecto aproximado en los grados-día acumulados abril-noviembre ({dias} días, Tbase 0): "
          f"{sesgo_tmean * dias:+.0f} °C·d")


if __name__ == "__main__":
    main()
