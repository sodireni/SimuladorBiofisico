"""
Extrae el suelo de SoilGrids por parcela y calcula la capacidad de agua con Saxton y Rawls (2006).

Pasos:
  1. Para cada capa (0-5, 5-15, 15-30, 30-60 cm), media de cada propiedad dentro del polígono de la
     parcela. Los píxeles con arcilla, arena, limo o densidad = 0 se tratan como SIN DATO (el raster
     no declara nodata, pero esos ceros no son suelo real). Si el polígono no toca píxeles válidos
     (parcela más chica que 250 m), se usan píxeles vecinos (hasta 3).
  2. Conversión de unidades de SoilGrids:  clay, sand, silt: g/kg -> /1000 = fracción;
     soc: dg/kg -> /100 = % de carbono orgánico; materia orgánica % = C org % * 1.724 (Van Bemmelen),
     acotada a 8 % (rango de validez de Saxton y Rawls); cfvo: cm3/dm3 -> /1000 = fracción;
     bdod: cg/cm3 -> /100 = g/cm3.
  3. Saxton y Rawls (2006) por capa: capacidad de campo (33 kPa), punto de marchitez (1500 kPa) y
     saturación, en fracción volumétrica de tierra fina.
  4. Lámina de agua en mm = fracción * espesor de la capa * (1 - grava). Las 4 capas suman 600 mm.
     La grava no retiene agua; se guarda también AWC_mm_sin_grava para sensibilidad.

Cita: Saxton, K. E. y Rawls, W. J. (2006). Soil water characteristic estimates by texture and
organic matter for hydrologic solutions. Soil Sci. Soc. Am. J., 70, 1569-1578.
(Verifiquen los coeficientes contra el artículo antes de entregar.)

Uso (desde la carpeta principal del proyecto):
    python src/ingest/extraer_suelo.py
Salida: data/processed/suelo_parcelas.csv
"""
import os

import numpy as np
import pandas as pd

SHP = "data/raw/Parcelas_Reto_AGC_CONJUNTO.shp"
DIR = "data/external/soilgrids"
SALIDA = "data/processed/suelo_parcelas.csv"
PROPS = ["clay", "sand", "silt", "bdod", "soc", "cfvo"]
ESPESOR_MM = {"0-5cm": 50, "5-15cm": 100, "15-30cm": 150, "30-60cm": 300}   # suman 600 mm
FACTOR_OM = 1.724
OM_MAX = 8.0


def saxton_rawls(S, C, OM):
    """S y C: fracciones (0-1). OM: % de materia orgánica. Devuelve (FC, PWP, saturación) volumétricos."""
    OM = np.clip(OM, 0.0, OM_MAX)
    t1500 = -0.024 * S + 0.487 * C + 0.006 * OM + 0.005 * S * OM - 0.013 * C * OM + 0.068 * S * C + 0.031
    pwp = t1500 + (0.14 * t1500 - 0.02)
    t33 = -0.251 * S + 0.195 * C + 0.011 * OM + 0.006 * S * OM - 0.027 * C * OM + 0.452 * S * C + 0.299
    fc = t33 + (1.283 * t33 ** 2 - 0.374 * t33 - 0.015)
    ts33 = 0.278 * S + 0.034 * C + 0.022 * OM - 0.018 * S * OM - 0.027 * C * OM - 0.584 * S * C + 0.078
    s33 = ts33 + (0.636 * ts33 - 0.107)
    sat = fc + s33 - 0.097 * S + 0.043
    return fc, pwp, sat


def calcular_suelo(largo):
    """largo: una fila por (ID_POLIGON, prof) con valores crudos de SoilGrids en clay, sand, silt,
    bdod, soc, cfvo. Devuelve una fila por parcela con el perfil 0-60 cm."""
    d = largo.copy()
    d["h"] = d["prof"].map(ESPESOR_MM)
    S, C = d["sand"] / 1000, d["clay"] / 1000
    d["oc_pct"] = d["soc"] / 100
    d["om_pct"] = np.clip(d["oc_pct"] * FACTOR_OM, 0, OM_MAX)
    d["om_sin_tope"] = d["oc_pct"] * FACTOR_OM
    d["fc"], d["pwp"], d["sat"] = saxton_rawls(S, C, d["om_pct"])
    grava = d["cfvo"] / 1000
    d["FC_mm"] = d["fc"] * d["h"] * (1 - grava)
    d["PWP_mm"] = d["pwp"] * d["h"] * (1 - grava)
    d["AWC_mm"] = (d["fc"] - d["pwp"]) * d["h"] * (1 - grava)
    d["AWC_mm_sin_grava"] = (d["fc"] - d["pwp"]) * d["h"]
    d["arcilla_pct"], d["arena_pct"], d["limo_pct"] = d["clay"] / 10, d["sand"] / 10, d["silt"] / 10
    d["bdod_g_cm3"], d["cfvo_pct"] = d["bdod"] / 100, d["cfvo"] / 10

    g = d.groupby("ID_POLIGON")
    suma = g[["FC_mm", "PWP_mm", "AWC_mm", "AWC_mm_sin_grava"]].agg(lambda x: x.sum(min_count=4))
    out = suma.copy()
    for col in ["arcilla_pct", "arena_pct", "limo_pct", "bdod_g_cm3", "cfvo_pct", "om_pct", "fc", "pwp", "sat"]:
        w = d["h"].where(d[col].notna())
        out[{"fc": "FC_vol", "pwp": "PWP_vol", "sat": "sat_vol"}.get(col, col)] = \
            (d[col] * d["h"]).groupby(d["ID_POLIGON"]).sum() / w.groupby(d["ID_POLIGON"]).sum()
    out["om_capas_topadas"] = (d["om_sin_tope"] > OM_MAX).groupby(d["ID_POLIGON"]).sum()
    out["n_capas"] = g["clay"].count()
    return out.reset_index()


def pixeles_parcela(geom, tr, shape, valido):
    from rasterio.features import geometry_mask
    from rasterio.transform import rowcol
    m = geometry_mask([geom], out_shape=shape, transform=tr, all_touched=True, invert=True) & valido
    if m.any():
        return m, "poligono"
    r, c = rowcol(tr, geom.centroid.x, geom.centroid.y)
    r, c = int(np.ravel(r)[0]), int(np.ravel(c)[0])
    for rad in range(4):
        w = np.zeros(shape, bool)
        w[max(r - rad, 0): r + rad + 1, max(c - rad, 0): c + rad + 1] = True
        w &= valido
        if w.any():
            return w, f"vecino_{rad}px"
    return None, "sin_dato"


def extraer_capas():
    import geopandas as gpd
    import rasterio
    gdf = gpd.read_file(SHP)
    filas, metodos, forma = [], [], None
    print("Píxeles inválidos (arcilla/arena/limo/densidad = 0) en el rectángulo descargado:")
    for prof in ESPESOR_MM:
        capas, tr = {}, None
        for p in PROPS:
            with rasterio.open(f"{DIR}/{p}_{prof}_mean.tif") as src:
                capas[p] = src.read(1).astype(float)
                tr = tr or src.transform
                assert forma in (None, src.shape), "Las capas no tienen la misma rejilla"
                forma = src.shape
        valido = np.all([capas[p] > 0 for p in ("clay", "sand", "silt", "bdod")], axis=0)
        print(f"  {prof:8s} {100 * (1 - valido.mean()):.1f} %")
        for i, geom in enumerate(gdf.geometry):
            m, metodo = pixeles_parcela(geom, tr, forma, valido)
            metodos.append({"ID_POLIGON": gdf["ID_POLIGON"].iloc[i], "prof": prof, "metodo": metodo})
            fila = {"ID_POLIGON": gdf["ID_POLIGON"].iloc[i], "prof": prof}
            for p in PROPS:
                fila[p] = capas[p][m].mean() if m is not None else np.nan
            filas.append(fila)
    return pd.DataFrame(filas), pd.DataFrame(metodos)


def main():
    largo, metodos = extraer_capas()
    print("\nMétodo de extracción por parcela y capa:", metodos["metodo"].value_counts().to_dict())
    res = calcular_suelo(largo)
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    res.to_csv(SALIDA, index=False)

    print(f"\nParcelas: {len(res)} | con las 4 capas: {int((res['n_capas'] == 4).sum())} "
          f"| parcelas con alguna capa sin dato: {int((res['n_capas'] < 4).sum())}")
    cols = ["arcilla_pct", "arena_pct", "limo_pct", "om_pct", "bdod_g_cm3", "cfvo_pct",
            "FC_vol", "PWP_vol", "FC_mm", "PWP_mm", "AWC_mm", "AWC_mm_sin_grava"]
    print(res[cols].describe().loc[["min", "25%", "50%", "75%", "max"]].round(2).to_string())
    suma = res["arcilla_pct"] + res["arena_pct"] + res["limo_pct"]
    print(f"\nArcilla+arena+limo (debe ser ~100): mín {suma.min():.1f}, máx {suma.max():.1f}")
    print(f"Parcelas con alguna capa de materia orgánica topada a {OM_MAX} %: "
          f"{int((res['om_capas_topadas'] > 0).sum())}")
    poro = 1 - res["bdod_g_cm3"] / 2.65
    print(f"Chequeo cruzado: porosidad por densidad (1 - bdod/2.65) = {poro.mean():.2f} | "
          f"saturación Saxton y Rawls = {res['sat_vol'].mean():.2f} | "
          f"correlación entre parcelas = {poro.corr(res['sat_vol']):.2f}")
    print("Guardado:", SALIDA)


if __name__ == "__main__":
    main()
