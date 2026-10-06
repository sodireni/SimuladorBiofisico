"""
MÓDULO 1: CLIMA E INTERPOLACIÓN: Simulador biofísico de cebada
Reto AgroCebada FIRA 2026

Entradas:
    data/processed/parcelas_base.csv              (ID_POLIGON, lat)
    data/external/clima_diario_parcelas_2025.csv  (clima diario por parcela)
Salida:
    data/processed/clima_m1_procesado.csv

Uso (desde la raíz del repositorio):
    python src/modules/m1_clima.py
"""

import os
import sys

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# CONSTANTES DEL CONTRATO DE DATOS
# ----------------------------------------------------------------------------
RUTA_PARCELAS = "data/processed/parcelas_base.csv"
RUTA_CLIMA = "data/external/clima_diario_parcelas_2025.csv"
DIR_SALIDA = "data/processed"
RUTA_SALIDA = os.path.join(DIR_SALIDA, "clima_m1_procesado.csv")

ID_COL = "ID_POLIGON"
FECHA_INI = pd.Timestamp("2025-03-15")
FECHA_FIN = pd.Timestamp("2025-11-30")
N_DIAS_ESPERADO = 261
N_PARCELAS_ESPERADO = 197

RENOMBRAR = {
    "temperature_2m_max": "tmax",
    "temperature_2m_min": "tmin",
    "precipitation_sum": "pcp",
    "shortwave_radiation_sum": "rs",
    "date": "fecha",
}

GSC = 0.0820            # Constante solar FAO-56 (MJ/m²/min)
FACTOR_PAR = 0.48       # Fracción PAR de la radiación global
LAMBDA_INV = 0.408      # MJ/m²/día -> mm/día equivalente de evaporación
LIMITE_INTERP_DIAS = 5  # Máximo de días consecutivos a interpolar


# ----------------------------------------------------------------------------
# MÓDULO 1 (FUNCIÓN PURA)
# ----------------------------------------------------------------------------
def modulo_1(df_clima_parcela: pd.DataFrame, lat_deg: float) -> pd.DataFrame:
    """
    Calcula tmean, par, ra y eto para una parcela.

    Parámetros
    ----------
    df_clima_parcela : DataFrame con columnas ['fecha', 'tmax', 'tmin', 'pcp', 'rs']
                       (y opcionalmente 'ID_POLIGON'), fecha en YYYY-MM-DD.
    lat_deg          : latitud de la parcela en grados decimales (EPSG:4326).

    Retorna
    -------
    DataFrame diario (ventana 2025-03-15 a 2025-11-30) con las columnas
    originales más: tmean, par, ra, eto.
    """
    df = df_clima_parcela.copy()

    # --- Fechas: normalizar, ordenar, filtrar ventana de simulación ---------
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.normalize()
    df = df.drop_duplicates(subset="fecha", keep="first").sort_values("fecha")
    df = df[(df["fecha"] >= FECHA_INI) & (df["fecha"] <= FECHA_FIN)]

    # --- Calendario completo (261 días) e interpolación de huecos -----------
    id_val = df[ID_COL].iloc[0] if (ID_COL in df.columns and len(df)) else None
    calendario = pd.date_range(FECHA_INI, FECHA_FIN, freq="D")
    df = df.set_index("fecha").reindex(calendario)
    df.index.name = "fecha"
    if id_val is not None:
        df[ID_COL] = id_val

    for col in ["tmax", "tmin", "pcp", "rs"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- 1. Verificación de unidades: Kelvin -> Celsius ---------------------
    for col in ["tmax", "tmin"]:
        es_kelvin = df[col] > 100
        df.loc[es_kelvin, col] = df.loc[es_kelvin, col] - 273.15

    # Interpolación temporal de huecos cortos (temperatura y radiación);
    # precipitación faltante se asume 0 mm (sin dato = sin lluvia registrada).
    for col in ["tmax", "tmin", "rs"]:
        df[col] = df[col].interpolate(method="linear", limit=LIMITE_INTERP_DIAS,
                                      limit_direction="both")
    df["pcp"] = df["pcp"].fillna(0.0).clip(lower=0.0)
    df["rs"] = df["rs"].clip(lower=0.0)

    # --- 2. Temperatura media ----------------------------------------------
    df["tmean"] = (df["tmax"] + df["tmin"]) / 2.0

    # --- 3. PAR (MJ/m²/día) -------------------------------------------------
    df["par"] = FACTOR_PAR * df["rs"]

    # --- 4. Radiación extraterrestre Ra: FAO-56 Ec. 21 ----------------------
    doy = df.index.dayofyear.to_numpy(dtype=float)
    phi = np.deg2rad(lat_deg)

    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi / 365.0 * doy)
    delta = 0.409 * np.sin(2.0 * np.pi / 365.0 * doy - 1.39)
    arg = np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0)
    ws = np.arccos(arg)

    ra = (24.0 * 60.0 / np.pi) * GSC * dr * (
        ws * np.sin(phi) * np.sin(delta)
        + np.cos(phi) * np.cos(delta) * np.sin(ws)
    )
    df["ra"] = np.maximum(ra, 0.0)

    # --- 5. ETo Hargreaves-Samani (mm/día) ---------------------------------
    rango_t = np.sqrt(np.maximum(0.0, df["tmax"] - df["tmin"]))
    df["eto"] = 0.0023 * LAMBDA_INV * df["ra"] * (df["tmean"] + 17.8) * rango_t
    df["eto"] = df["eto"].clip(lower=0.0)

    return df.reset_index()


# ----------------------------------------------------------------------------
# CARGA DE DATOS
# ----------------------------------------------------------------------------
def cargar_parcelas(ruta: str) -> pd.DataFrame:
    df = pd.read_csv(ruta)
    faltan = {ID_COL, "lat"} - set(df.columns)
    if faltan:
        raise KeyError(f"parcelas_base.csv no contiene las columnas: {faltan}")
    df = df[[ID_COL, "lat"]].copy()
    df[ID_COL] = df[ID_COL].astype(str).str.strip()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df = df.dropna(subset=["lat"]).drop_duplicates(subset=ID_COL, keep="first")
    return df


def cargar_clima(ruta: str) -> pd.DataFrame:
    df = pd.read_csv(ruta)
    df = df.rename(columns=RENOMBRAR)

    requeridas = {ID_COL, "fecha", "tmax", "tmin", "pcp", "rs"}
    faltan = requeridas - set(df.columns)
    if faltan:
        raise KeyError(f"clima_diario_parcelas_2025.csv no contiene: {faltan}")

    df = df[list(requeridas)].copy()
    df[ID_COL] = df[ID_COL].astype(str).str.strip()
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.normalize()
    return df


# ----------------------------------------------------------------------------
# VALIDACIÓN
# ----------------------------------------------------------------------------
def validar(df: pd.DataFrame) -> bool:
    print("\n" + "=" * 70)
    print("VALIDACIÓN AUTOMÁTICA: MÓDULO 1")
    print("=" * 70)
    ok = True

    n_parc = df[ID_COL].nunique()
    n_dias = df.groupby(ID_COL)["fecha"].nunique()
    print(f"Parcelas procesadas : {n_parc} (esperadas: {N_PARCELAS_ESPERADO})")
    print(f"Días por parcela    : min={n_dias.min()}, max={n_dias.max()} "
          f"(esperados: {N_DIAS_ESPERADO})")
    print(f"Filas totales       : {len(df):,}")
    print(f"Rango de fechas     : {df['fecha'].min():%Y-%m-%d} -> "
          f"{df['fecha'].max():%Y-%m-%d}")
    if n_parc != N_PARCELAS_ESPERADO or (n_dias != N_DIAS_ESPERADO).any():
        print("⚠️  ADVERTENCIA: cobertura distinta a la esperada.")
        ok = False

    cols = ["tmax", "tmin", "pcp", "rs", "tmean", "par", "ra", "eto"]
    nulos = df[cols].isna().sum()
    if nulos.sum() == 0:
        print("✅ Sin valores nulos (NaN) en las variables procesadas.")
    else:
        print("❌ Se encontraron NaN:")
        print(nulos[nulos > 0].to_string())
        ok = False

    n_eto_neg = int((df["eto"] < 0).sum())
    if n_eto_neg == 0:
        print("✅ Sin valores anómalos de ETo < 0.")
    else:
        print(f"❌ {n_eto_neg} registros con ETo < 0.")
        ok = False

    print("\nResumen estadístico (media, min, max):")
    resumen = df[["tmean", "par", "ra", "eto"]].agg(["mean", "min", "max"]).T
    resumen.columns = ["media", "min", "max"]
    print(resumen.round(3).to_string())
    print("=" * 70)
    return ok


# ----------------------------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    print("Cargando datos...")
    parcelas = cargar_parcelas(RUTA_PARCELAS)
    clima = cargar_clima(RUTA_CLIMA)
    print(f"  Parcelas base : {len(parcelas)}")
    print(f"  Registros clima: {len(clima):,}")

    # Agrupar clima por parcela una sola vez (evita filtrar 197 veces)
    grupos = dict(tuple(clima.groupby(ID_COL, sort=False)))

    resultados = []
    sin_clima = []

    for id_poligon, lat in zip(parcelas[ID_COL], parcelas["lat"]):
        df_p = grupos.get(id_poligon)
        if df_p is None or df_p.empty:
            sin_clima.append(id_poligon)
            continue
        resultados.append(modulo_1(df_p, float(lat)))

    if sin_clima:
        print(f"⚠️  {len(sin_clima)} parcelas sin datos climáticos: "
              f"{sin_clima[:10]}{'...' if len(sin_clima) > 10 else ''}")
    if not resultados:
        sys.exit("ERROR: no se pudo procesar ninguna parcela.")

    df_final = pd.concat(resultados, ignore_index=True)

    orden = [ID_COL, "fecha", "tmax", "tmin", "tmean", "pcp", "rs", "par", "ra", "eto"]
    df_final = df_final[orden].sort_values([ID_COL, "fecha"]).reset_index(drop=True)
    df_final["fecha"] = df_final["fecha"].dt.strftime("%Y-%m-%d")

    # La validación usa fechas como datetime
    validar(df_final.assign(fecha=pd.to_datetime(df_final["fecha"])))

    os.makedirs(DIR_SALIDA, exist_ok=True)
    df_final.to_csv(RUTA_SALIDA, index=False)
    print(f"\n💾 Archivo guardado en: {RUTA_SALIDA}")
    print(f"   Dimensiones: {df_final.shape[0]:,} filas × {df_final.shape[1]} columnas")