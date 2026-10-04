"""
¿Captura cada fuente de temperatura la altitud de las parcelas?

Para cada mes y variable (Tmax, Tmin), ajusta una recta  temperatura = a + b * elevación  entre las
197 parcelas, para Open-Meteo y para CHIRTS-ERA5. El gradiente físico esperado en montaña es
aproximadamente -5 a -7 °C por km (más frío al subir). Una fuente cuyo gradiente sea ~0 o positivo
NO está representando la altitud de las parcelas.

Requiere: data/processed/topografia_parcelas.csv (extraer_topografia.py) y qc_temperatura_vs_chirts.py
en la misma carpeta.

Uso (desde la carpeta principal del proyecto):
    python src/ingest/qc_gradiente_altitud.py
"""
import numpy as np
import pandas as pd

import qc_temperatura_vs_chirts as q

TOPO = "data/processed/topografia_parcelas.csv"


def gradiente_por_km(elev, temp):
    """Pendiente (°C por km) de la recta temp ~ elev, ignorando NaN."""
    ok = ~(np.isnan(elev) | np.isnan(temp))
    if ok.sum() < 5 or np.std(elev[ok]) == 0:
        return np.nan
    return float(np.polyfit(elev[ok], temp[ok], 1)[0] * 1000)


def main():
    coords = pd.read_csv(q.COORDS)
    ids = coords["ID_POLIGON"]
    elev = (pd.read_csv(TOPO).set_index("ID_POLIGON")["elev_m"].reindex(ids).to_numpy())
    clima = pd.read_csv(q.CLIMA, parse_dates=["fecha"])
    clima["mes"] = clima["fecha"].dt.month
    print(f"Elevación de las parcelas: {np.nanmin(elev):.0f} a {np.nanmax(elev):.0f} m "
          f"(desv. estándar {np.nanstd(elev):.0f} m)\n")

    for var, col in q.VARIABLES.items():
        filas = []
        for mes in q.MESES:
            om = clima[clima["mes"] == mes].groupby("ID_POLIGON")[col].mean().reindex(ids).to_numpy()
            ch = q.muestrear_chirts(var, mes, coords)
            filas.append({"mes": mes, "OpenMeteo_C_por_km": gradiente_por_km(elev, om),
                          "CHIRTS_C_por_km": gradiente_por_km(elev, ch)})
        t = pd.DataFrame(filas).set_index("mes").round(1)
        print(f"{var}: gradiente con la altitud (°C por km; esperado ~ -5 a -7)\n{t.to_string()}")
        print(f"  promedio: Open-Meteo {t['OpenMeteo_C_por_km'].mean():.1f} | "
              f"CHIRTS {t['CHIRTS_C_por_km'].mean():.1f}\n")


if __name__ == "__main__":
    main()
