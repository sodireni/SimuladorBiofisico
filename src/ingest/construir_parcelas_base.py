"""
Arma data/processed/parcelas_base.csv: UNA fila por parcela con todo lo estático que necesita el
simulador (ubicación, topografía, fecha de siembra y suelo). Es la entrada de los 4 módulos.

NO incluye rendimiento (evita fuga de datos): el equipo de ML lo une por su cuenta.
Las series diarias (clima y satélite) se quedan en sus propios archivos; ver docs/CONTRATO_DE_DATOS.md.

Siembra de las parcelas con doble ciclo: se guardan los dos escenarios (A = primer ciclo,
B = ciclo principal) y 'fecha_siembra' toma el que indique configs/params.yaml
(siembra.escenario_doble_ciclo, por defecto "A"). En parcelas de ciclo simple A = B.

Requiere haber corrido: extraer_topografia.py, estimar_siembra.py, extraer_suelo.py.

Uso (desde la carpeta principal del proyecto):
    python src/ingest/construir_parcelas_base.py
"""
import numpy as np
import pandas as pd
import yaml

SHP = "data/raw/Parcelas_Reto_AGC_CONJUNTO.shp"
COORDS = "data/processed/coordenadas_parcelas.csv"
TOPO = "data/processed/topografia_parcelas.csv"
SIEMBRA = "data/processed/siembra_estimada.csv"
SUELO = "data/processed/suelo_parcelas.csv"
PARAMS = "configs/params.yaml"
SALIDA = "data/processed/parcelas_base.csv"

N_ESPERADO = 197
CONJUNTOS_ESPERADOS = {"ENTRENAMIENTO": 138, "PREDICCION": 59}
VENTANA = (pd.Timestamp("2025-03-15"), pd.Timestamp("2025-11-30"))
COLS_SUELO = ["arcilla_pct", "arena_pct", "limo_pct", "om_pct", "bdod_g_cm3", "cfvo_pct",
              "FC_vol", "PWP_vol", "FC_mm", "PWP_mm", "AWC_mm", "AWC_mm_sin_grava"]
OBLIGATORIAS = ["lat", "lon", "elev_m", "pendiente_pct", "fecha_siembra", "FC_mm", "PWP_mm", "AWC_mm"]


def leer_meta(ruta):
    import geopandas as gpd
    g = gpd.read_file(ruta)
    meta = g[["ID_POLIGON", "CONJUNTO", "Estado", "Municipio", "área_ha"]].copy()
    return meta.rename(columns={"área_ha": "area_ha"})


def armar_base(meta, coords, topo, siembra, suelo, escenario="A"):
    if escenario not in ("A", "B"):
        raise ValueError("escenario_doble_ciclo debe ser 'A' o 'B'")
    c = coords.rename(columns={"latitud": "lat", "longitud": "lon"})[["ID_POLIGON", "lat", "lon"]]
    t = topo[["ID_POLIGON", "elev_m", "pendiente_deg", "pendiente_pct"]]
    s = siembra[["ID_POLIGON", "doble_ciclo", "fecha_siembra", "fecha_siembra_A", "fecha_sos",
                 "fecha_pico", "ndvi_pico", "flag_calidad"]].rename(
        columns={"fecha_siembra": "fecha_siembra_B", "flag_calidad": "flag_siembra"})
    s["doble_ciclo"] = s["doble_ciclo"].fillna(False).astype(bool)
    s["fecha_siembra_A"] = s["fecha_siembra_A"].fillna(s["fecha_siembra_B"])
    u = suelo[["ID_POLIGON", *COLS_SUELO]]

    b = meta
    for tabla in (c, t, s, u):
        b = b.merge(tabla, on="ID_POLIGON", how="left", validate="1:1")
    for col in ("fecha_siembra_A", "fecha_siembra_B", "fecha_sos", "fecha_pico"):
        b[col] = pd.to_datetime(b[col])
    b["fecha_siembra"] = b["fecha_siembra_A"] if escenario == "A" else b["fecha_siembra_B"]
    b["fecha_siembra"] = np.where(b["doble_ciclo"], b["fecha_siembra"], b["fecha_siembra_B"])
    b["fecha_siembra"] = pd.to_datetime(b["fecha_siembra"])

    orden = ["ID_POLIGON", "CONJUNTO", "Estado", "Municipio", "area_ha", "lat", "lon",
             "elev_m", "pendiente_deg", "pendiente_pct",
             "fecha_siembra", "fecha_siembra_A", "fecha_siembra_B", "doble_ciclo", "flag_siembra",
             "fecha_sos", "fecha_pico", "ndvi_pico", *COLS_SUELO]
    return b[orden].sort_values("ID_POLIGON").reset_index(drop=True)


def verificar(b):
    """Devuelve una lista de problemas encontrados (vacía si todo está bien)."""
    p = []
    if len(b) != N_ESPERADO:
        p.append(f"hay {len(b)} filas y se esperaban {N_ESPERADO}")
    if b["ID_POLIGON"].duplicated().any():
        p.append("hay ID_POLIGON repetidos")
    for col in OBLIGATORIAS:
        n = int(b[col].isna().sum())
        if n:
            p.append(f"{n} parcelas sin valor en {col}")
    conteo = b["CONJUNTO"].value_counts().to_dict()
    if conteo != CONJUNTOS_ESPERADOS:
        p.append(f"CONJUNTO {conteo}, se esperaba {CONJUNTOS_ESPERADOS}")
    if (b["FC_mm"] <= b["PWP_mm"]).any():
        p.append("hay parcelas con FC_mm <= PWP_mm")
    fuera = ((b["fecha_siembra"] < VENTANA[0]) | (b["fecha_siembra"] > VENTANA[1])).sum()
    if fuera:
        p.append(f"{int(fuera)} fechas de siembra fuera de la ventana {VENTANA[0].date()}..{VENTANA[1].date()}")
    tarde = (b["fecha_siembra"] >= b["fecha_pico"]).sum()
    if tarde:
        p.append(f"{int(tarde)} parcelas con siembra posterior o igual a la fecha del pico de NDVI")
    return p


def main():
    try:
        escenario = yaml.safe_load(open(PARAMS))["siembra"].get("escenario_doble_ciclo", "A")
    except (FileNotFoundError, KeyError):
        escenario = "A"
    print(f"Escenario de siembra para parcelas de doble ciclo: {escenario}")

    b = armar_base(leer_meta(SHP), pd.read_csv(COORDS), pd.read_csv(TOPO),
                   pd.read_csv(SIEMBRA), pd.read_csv(SUELO), escenario)
    problemas = verificar(b)

    salida = b.copy()
    for col in ("fecha_siembra", "fecha_siembra_A", "fecha_siembra_B", "fecha_sos", "fecha_pico"):
        salida[col] = salida[col].dt.strftime("%Y-%m-%d")
    salida.to_csv(SALIDA, index=False)

    print(f"\nFilas: {len(b)} | columnas: {b.shape[1]}")
    print("CONJUNTO:", b["CONJUNTO"].value_counts().to_dict(),
          "| Estado:", b["Estado"].value_counts().to_dict())
    print("Doble ciclo:", int(b["doble_ciclo"].sum()),
          "| flags de siembra:", b["flag_siembra"].value_counts().to_dict())
    dif = (b.loc[b["doble_ciclo"], "fecha_siembra_B"] - b.loc[b["doble_ciclo"], "fecha_siembra_A"]).dt.days
    if len(dif):
        print(f"En doble ciclo, B - A: mediana {dif.median():.0f} días (mín {dif.min()}, máx {dif.max()})")
    print("\nResumen numérico:")
    print(b[["area_ha", "elev_m", "pendiente_pct", "AWC_mm", "FC_mm", "PWP_mm"]]
          .describe().loc[["min", "50%", "max"]].round(1).to_string())
    print("\nVerificación:", "TODO BIEN" if not problemas else "")
    for x in problemas:
        print("  PROBLEMA:", x)
    print("Guardado:", SALIDA)


if __name__ == "__main__":
    main()
