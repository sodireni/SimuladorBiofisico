"""
Limpia las series satelitales y las lleva a escala DIARIA para el ciclo 2025.

Series que produce (una columna por fuente, NUNCA se mezclan sensores):
  - fapar_s2    : FAPAR de Sentinel-2 (Dataset Básico)  -> entrada de fPAR del Módulo 4
  - ndvi_planet : NDVI de Planet (Dataset PRO)          -> apoyo para estimar la siembra

Pasos por parcela y fuente:
  1. Quedarse con el sensor correspondiente y con fechas del ciclo (+ margen en los bordes).
  2. Descartar observaciones con nubosidad > NUB_MAX y valores vacíos.
  3. Promediar fechas repetidas y recortar a un rango físico válido.
  4. Quitar picos aislados (contra la mediana móvil de 5 observaciones).
  5. Interpolación lineal en el tiempo + suavizado Savitzky-Golay (grado 2).
  6. Recortar al ciclo INI..FIN.

Uso (desde la carpeta principal del proyecto):
    python src/ingest/limpiar_satelite.py

Salidas:
    data/processed/series_satelite_diarias_2025.csv
    docs/fig_satelite_qc.png   (6 parcelas al azar: observaciones vs. serie suavizada)
"""
import os

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

BASICO = "data/raw/Conjunto_datos_BASICO_AgroCebada2026.csv"
PRO = "data/raw/Conjunto_datos_PRO_AgroCebada.csv"
COORDS = "data/processed/coordenadas_parcelas.csv"
SALIDA = "data/processed/series_satelite_diarias_2025.csv"
FIGURA = "docs/fig_satelite_qc.png"

INI, FIN = pd.Timestamp("2025-03-15"), pd.Timestamp("2025-11-30")
MARGEN = pd.Timedelta(days=30)     # evita huecos en los bordes al interpolar
NUB_MAX = 20.0                     # % de nubosidad máxima aceptada (ajustable)
MIN_OBS = 5                        # mínimo de observaciones válidas por parcela

# nombre_salida, archivo, sensor, columna, mínimo, máximo, ventana_suavizado(días), umbral_pico
FUENTES = [
    ("fapar_s2", BASICO, "Sentinel-2", "fapar_promedio", 0.0, 1.0, 21, 0.25),
    ("ndvi_planet", PRO, "Planet", "ndvi_promedio", -0.1, 1.0, 15, 0.25),
]


def cargar(ruta, sensor, col):
    d = pd.read_csv(ruta, usecols=["ID_POLIGONO", "fecha_captura", "sensor", col,
                                   "porcentaje_nubosidad"])
    d = d[d["sensor"] == sensor].copy()
    d["fecha"] = pd.to_datetime(d["fecha_captura"], format="%d/%m/%Y", errors="coerce")
    d = d.rename(columns={"ID_POLIGONO": "ID_POLIGON"})
    d = d[(d["fecha"] >= INI - MARGEN) & (d["fecha"] <= FIN + MARGEN)]
    return d


def serie_diaria(obs, col, lo, hi, ventana, umbral):
    """obs: observaciones (fecha, col) de UNA parcela. Devuelve (serie diaria, obs usadas, hueco máx)."""
    s = obs.groupby("fecha")[col].mean().clip(lo, hi).sort_index()
    if len(s) >= 3:
        mediana = s.rolling(5, center=True, min_periods=3).median()
        s = s[(s - mediana).abs() <= umbral]
    en_ciclo = s[(s.index >= INI) & (s.index <= FIN)]
    if len(en_ciclo) < MIN_OBS:
        return None, len(en_ciclo), np.nan
    puntos = pd.Series([INI, *en_ciclo.index, FIN])
    hueco = int(puntos.diff().dt.days.max())

    idx = pd.date_range(INI - MARGEN, FIN + MARGEN)
    d = s.reindex(idx).interpolate(method="time", limit_area="inside").ffill().bfill()
    v = savgol_filter(d.values, ventana, 2)
    d = pd.Series(np.clip(v, lo, hi), index=idx)
    return d[(d.index >= INI) & (d.index <= FIN)], len(en_ciclo), hueco


def main():
    parcelas = pd.read_csv(COORDS)["ID_POLIGON"].tolist()
    base = pd.MultiIndex.from_product(
        [parcelas, pd.date_range(INI, FIN)], names=["ID_POLIGON", "fecha"]
    ).to_frame(index=False)
    crudas = {}

    for nombre, ruta, sensor, col, lo, hi, vent, umbral in FUENTES:
        print("=" * 70, f"\n{nombre}  ({sensor}, columna {col})")
        d = cargar(ruta, sensor, col)
        n0 = len(d)
        print(f"Filas del sensor en el ciclo (+margen): {n0}"
              f" | fechas ilegibles: {int(d['fecha'].isna().sum())}")
        d = d.dropna(subset=["fecha"])
        con_valor = d.dropna(subset=[col])
        print(f"Con valor en {col}: {len(con_valor)} ({100 * len(con_valor) / max(n0, 1):.0f} %)")
        print(f"Rango crudo de {col}: {con_valor[col].min():.3f} a {con_valor[col].max():.3f}"
              f" | mediana {con_valor[col].median():.3f}")
        limpio = con_valor[con_valor["porcentaje_nubosidad"] <= NUB_MAX]
        print(f"Con nubosidad <= {NUB_MAX:.0f} %: {len(limpio)}"
              f" ({100 * len(limpio) / max(len(con_valor), 1):.0f} % de las que tenían valor)")

        filas, resumen = [], []
        for pid, g in limpio.groupby("ID_POLIGON"):
            serie, n, hueco = serie_diaria(g[["fecha", col]], col, lo, hi, vent, umbral)
            resumen.append((pid, n, hueco))
            if serie is not None:
                filas.append(pd.DataFrame({"ID_POLIGON": pid, "fecha": serie.index,
                                           nombre: serie.values.round(4)}))
                crudas[(nombre, pid)] = (g.groupby("fecha")[col].mean(), serie)
        base = base.merge(pd.concat(filas), on=["ID_POLIGON", "fecha"], how="left")

        r = pd.DataFrame(resumen, columns=["ID_POLIGON", "n_obs", "hueco_max_dias"])
        r = r.set_index("ID_POLIGON").reindex(parcelas)
        r["n_obs"] = r["n_obs"].fillna(0)
        sin = r.index[r["hueco_max_dias"].isna()].tolist()
        print(f"Parcelas con serie: {len(parcelas) - len(sin)}/{len(parcelas)}")
        print("Observaciones válidas por parcela en el ciclo (min, p25, mediana, p75, max):",
              r["n_obs"].quantile([0, .25, .5, .75, 1]).round(0).astype(int).tolist())
        print("Hueco máximo entre observaciones, días (mediana, p75, p90, max):",
              r["hueco_max_dias"].quantile([.5, .75, .9, 1]).round(0).tolist())
        print("Parcelas con hueco > 30 días:", int((r["hueco_max_dias"] > 30).sum()))
        if sin:
            print("Parcelas SIN serie:", sin)

    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    base.to_csv(SALIDA, index=False)
    print("\nGuardado:", SALIDA, base.shape)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        rng = np.random.default_rng(1)
        elegidas = rng.choice(parcelas, 6, replace=False)
        fig, ejes = plt.subplots(2, 3, figsize=(14, 7), sharey=True)
        for ax, pid in zip(ejes.ravel(), elegidas):
            for nombre, color in [("fapar_s2", "tab:green"), ("ndvi_planet", "tab:blue")]:
                if (nombre, pid) in crudas:
                    obs, ser = crudas[(nombre, pid)]
                    ax.plot(obs.index, obs.values, ".", color=color, alpha=.35, ms=4)
                    ax.plot(ser.index, ser.values, "-", color=color, lw=1.5, label=nombre)
            ax.set_title(pid)
            ax.tick_params(axis="x", rotation=45)
        ejes[0, 0].legend()
        fig.suptitle("Observaciones (puntos) y serie diaria suavizada (línea)")
        fig.tight_layout()
        os.makedirs(os.path.dirname(FIGURA), exist_ok=True)
        fig.savefig(FIGURA, dpi=110)
        print("Figura:", FIGURA)
    except ImportError:
        print("matplotlib no está instalado: se omite la figura (pip install matplotlib).")


if __name__ == "__main__":
    main()
