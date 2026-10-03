"""
Convierte el NDVI diario de Planet en un fPAR diario, calibrado contra el FAPAR de Sentinel-2.

Motivo: Sentinel-2 tiene un hueco de ~4 semanas en junio-julio (nubosidad), justo cuando
arranca el cultivo. Planet tiene muchas más observaciones, pero es NDVI, no FAPAR.

Método (no usa rendimiento, por lo que no hay fuga de datos):
  1. Parear, por parcela y fecha, cada observación válida de FAPAR (Sentinel-2) con el NDVI
     suavizado de Planet de ese mismo día.
  2. Ajuste lineal robusto  FAPAR = a * NDVI + b  (se descartan iterativamente los puntos
     con residuo > 3 desviaciones robustas MAD).
  3. fapar_final = clip(a * ndvi_planet + b, 0, 0.95) para todos los días del ciclo.

Requiere haber corrido antes limpiar_satelite.py.

Uso (desde la carpeta principal del proyecto):
    python src/ingest/calibrar_fpar.py

Salidas:
    data/processed/series_satelite_diarias_2025.csv   (se le agrega la columna fapar_final)
    docs/fig_calibracion_fpar.png
"""
import numpy as np
import pandas as pd

import limpiar_satelite as ls   # mismo folder: reutiliza rutas, filtros y funciones

FIGURA = "docs/fig_calibracion_fpar.png"


def main():
    ser = pd.read_csv(ls.SALIDA, parse_dates=["fecha"])
    ser = ser.drop(columns=["fapar_final"], errors="ignore")

    obs = ls.cargar(ls.BASICO, "Sentinel-2", "fapar_promedio")
    obs = obs.dropna(subset=["fecha", "fapar_promedio"])
    obs = obs[obs["porcentaje_nubosidad"] <= ls.NUB_MAX]
    obs = obs.groupby(["ID_POLIGON", "fecha"], as_index=False)["fapar_promedio"].mean()

    par = obs.merge(ser[["ID_POLIGON", "fecha", "ndvi_planet"]],
                    on=["ID_POLIGON", "fecha"]).dropna().reset_index(drop=True)
    x, y = par["ndvi_planet"].to_numpy(), par["fapar_promedio"].to_numpy()

    usar = np.ones(len(x), bool)
    for _ in range(4):
        a, b = np.polyfit(x[usar], y[usar], 1)
        res = y - (a * x + b)
        mad = 1.4826 * np.median(np.abs(res[usar] - np.median(res[usar])))
        usar = np.abs(res) <= 3 * mad
    a, b = np.polyfit(x[usar], y[usar], 1)
    res = y - (a * x + b)
    r2 = 1 - np.sum(res[usar] ** 2) / np.sum((y[usar] - y[usar].mean()) ** 2)

    print(f"Pares (parcela, fecha) con ambos sensores: {len(par)}")
    print(f"Usados en el ajuste: {usar.sum()} ({100 * usar.mean():.1f} %)")
    print(f"FAPAR = {a:.3f} * NDVI + ({b:.3f})")
    print(f"R2 = {r2:.3f} | RMSE = {np.sqrt(np.mean(res[usar] ** 2)):.3f}")

    par["residuo"] = res
    par["descartado"] = ~usar
    par["mes"] = par["fecha"].dt.to_period("M").astype(str)
    por_mes = par.groupby("mes").agg(
        pares=("residuo", "size"),
        sesgo=("residuo", "mean"),
        rmse=("residuo", lambda r: float(np.sqrt(np.mean(r ** 2)))),
        pct_descartado=("descartado", lambda d: 100 * float(d.mean())),
    ).round(3)
    print("\nAjuste por mes (sesgo = FAPAR observado - estimado):")
    print(por_mes.to_string())

    f = par.groupby("fecha")["descartado"].agg(["mean", "size"])
    malas = f[(f["mean"] > 0.5) & (f["size"] >= 20)]
    print("\nFechas de Sentinel-2 donde >50 % de las parcelas NO concuerdan con Planet:")
    print("(ninguna)" if malas.empty else
          malas.rename(columns={"mean": "frac_descartada", "size": "parcelas"}).round(2).to_string())

    ser["fapar_final"] = np.clip(a * ser["ndvi_planet"] + b, 0, 0.95).round(4)
    ser.to_csv(ls.SALIDA, index=False)
    print("\nColumna fapar_final agregada a", ls.SALIDA)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(x[usar], y[usar], s=4, alpha=.25, label="usados")
        ax.scatter(x[~usar], y[~usar], s=6, color="red", alpha=.5, label="descartados")
        xs = np.linspace(x.min(), x.max(), 50)
        ax.plot(xs, a * xs + b, "k-", label=f"FAPAR = {a:.2f}*NDVI {b:+.2f}")
        ax.set_xlabel("NDVI Planet (suavizado)")
        ax.set_ylabel("FAPAR Sentinel-2 (observado)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIGURA, dpi=110)
        print("Figura:", FIGURA)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
