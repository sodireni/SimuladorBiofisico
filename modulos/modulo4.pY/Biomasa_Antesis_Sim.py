"""Módulo 4: biomasa por eficiencia de uso de luz y ajuste de HI.

Lee ``simulacion_m1_m3.csv`` sin modificarlo. Al ejecutar este archivo crea
``resultados_modulo4.csv`` en esta misma carpeta, con una fila por parcela.
No requiere instalar paquetes externos.
"""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# Parámetros confirmados para el módulo 4.
RUE = 2.5  # g de biomasa por MJ de PAR absorbida
HI_BASE = 0.45
SENSIBILIDAD_ANTESIS = 0.5
SENSIBILIDAD_LLENADO = 0.3

ENTRADA = Path(__file__).resolve().parents[3] / "simulacion_m1_m3.csv"
SALIDA = Path(__file__).resolve().with_name("resultados_modulo4.csv")
COLUMNAS_REQUERIDAS = {
    "ID_POLIGON", "fecha", "par", "fapar_final", "ks", "fecha_siembra",
    "fecha_antesis", "fecha_madurez", "estadio",
}


def _fecha(valor: str, columna: str, fila: int) -> datetime:
    """Convierte una fecha ISO del CSV e informa la columna y fila si falla."""
    try:
        return datetime.strptime(valor, "%Y-%m-%d")
    except (TypeError, ValueError) as error:
        raise ValueError(f"Fecha inválida en {columna}, fila {fila}: {valor!r}") from error


def _numero(valor: str, columna: str, fila: int) -> float:
    """Convierte un número del CSV e informa la columna y fila si falla."""
    try:
        return float(valor)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Valor inválido en {columna}, fila {fila}: {valor!r}") from error


def _leer_entrada(ruta_entrada: Path) -> dict[str, list[dict]]:
    """Lee y valida solamente las entradas que necesita el módulo 4."""
    if not ruta_entrada.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de entrada: {ruta_entrada}")

    parcelas = defaultdict(list)
    fechas_vistas = set()
    with ruta_entrada.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames is None:
            raise ValueError("El archivo de entrada no tiene encabezados.")
        faltantes = COLUMNAS_REQUERIDAS.difference(lector.fieldnames)
        if faltantes:
            raise ValueError("Faltan columnas: " + ", ".join(sorted(faltantes)))

        for fila, registro in enumerate(lector, start=2):
            id_poligon = registro["ID_POLIGON"].strip()
            if not id_poligon:
                raise ValueError(f"ID_POLIGON vacío en la fila {fila}.")
            fecha = _fecha(registro["fecha"], "fecha", fila)
            clave = (id_poligon, fecha)
            if clave in fechas_vistas:
                raise ValueError(f"Registro repetido para {id_poligon} en {fecha.date()}.")
            fechas_vistas.add(clave)

            par = _numero(registro["par"], "par", fila)
            fpar = _numero(registro["fapar_final"], "fapar_final", fila)
            ks = _numero(registro["ks"], "ks", fila)
            if par < 0 or fpar < 0 or not 0 <= ks <= 1:
                raise ValueError(f"Valores físicos inválidos en la fila {fila}: PAR/fPAR >= 0 y 0 <= Ks <= 1.")

            parcelas[id_poligon].append({
                "fecha": fecha,
                "par": par,
                "fpar": min(fpar, 1.0),
                "ks": ks,
                "siembra": _fecha(registro["fecha_siembra"], "fecha_siembra", fila),
                "antesis": _fecha(registro["fecha_antesis"], "fecha_antesis", fila),
                "madurez": _fecha(registro["fecha_madurez"], "fecha_madurez", fila),
                "estadio": registro["estadio"].strip(),
            })

    if not parcelas:
        raise ValueError("El archivo de entrada no contiene registros.")
    return parcelas


def calcular_modulo4(ruta_entrada: Path = ENTRADA) -> list[dict]:
    """Devuelve las cuatro salidas de M4, una fila por parcela.

    fPAR ya está calculado como ``fapar_final`` en el CSV y se usa directamente.
    dBIO = PAR * fPAR * RUE * Ks * 10, donde 10 convierte g/m²/día en kg/ha/día.
    La biomasa se acumula solamente entre la siembra y la madurez, inclusive.
    """
    parcelas = _leer_entrada(ruta_entrada)
    resultados = []

    for id_poligon in sorted(parcelas):
        registros = sorted(parcelas[id_poligon], key=lambda registro: registro["fecha"])
        calendario = (registros[0]["siembra"], registros[0]["antesis"], registros[0]["madurez"])
        if calendario[2] < calendario[0]:
            raise ValueError(f"Madurez anterior a siembra en la parcela {id_poligon}.")
        if any((r["siembra"], r["antesis"], r["madurez"]) != calendario for r in registros):
            raise ValueError(f"Las fechas fenológicas cambian dentro de la parcela {id_poligon}.")

        siembra, antesis, madurez = calendario
        biomasa = 0.0
        fpar_integrado = 0.0
        biomasa_antesis = None
        biomasa_madurez = None
        ks_antesis = []
        ks_llenado = []

        for registro in registros:
            fecha = registro["fecha"]
            if siembra <= fecha <= madurez:
                fpar_integrado += registro["fpar"]
                dbio = registro["par"] * registro["fpar"] * RUE * registro["ks"] * 10.0
                biomasa += dbio

            if registro["estadio"] == "antesis":
                ks_antesis.append(registro["ks"])
            elif registro["estadio"] == "llenado":
                ks_llenado.append(registro["ks"])

            if fecha == antesis:
                biomasa_antesis = biomasa
            if fecha == madurez:
                biomasa_madurez = biomasa

        if biomasa_antesis is None or biomasa_madurez is None:
            raise ValueError(f"La serie de {id_poligon} no incluye el día de antesis o madurez.")
        if not ks_antesis or not ks_llenado:
            raise ValueError(f"La parcela {id_poligon} no tiene días de antesis o llenado.")

        promedio_antesis = sum(ks_antesis) / len(ks_antesis)
        promedio_llenado = sum(ks_llenado) / len(ks_llenado)
        penal_antesis = SENSIBILIDAD_ANTESIS * (1.0 - promedio_antesis)
        penal_llenado = SENSIBILIDAD_LLENADO * (1.0 - promedio_llenado)
        hi_penalizado = HI_BASE * (1.0 - penal_antesis - penal_llenado)
        hi_penalizado = max(0.0, min(HI_BASE, hi_penalizado))

        resultados.append({
            "ID_POLIGON": id_poligon,
            "fPAR_integrado": fpar_integrado,
            "Biomasa_Antesis_Sim": biomasa_antesis,
            "Biomasa_Total_Sim": biomasa_madurez,
            "HI_penalizado": hi_penalizado,
        })

    return resultados


def guardar_resultados(resultados: list[dict], ruta_salida: Path = SALIDA) -> None:
    """Guarda la matriz final de las cuatro variables de M4."""
    columnas = [
        "ID_POLIGON", "fPAR_integrado", "Biomasa_Antesis_Sim",
        "Biomasa_Total_Sim", "HI_penalizado",
    ]
    with ruta_salida.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        for resultado in resultados:
            escritor.writerow({
                columna: resultado[columna] if columna == "ID_POLIGON" else f"{resultado[columna]:.6f}"
                for columna in columnas
            })


def main() -> None:
    resultados = calcular_modulo4()
    guardar_resultados(resultados)
    print("Módulo 4 ejecutado correctamente.")
    print(f"Resultado: {SALIDA}")
    print(f"Parcelas procesadas: {len(resultados)}")
    for resultado in resultados:
        print(
            f"{resultado['ID_POLIGON']}: "
            f"fPAR={resultado['fPAR_integrado']:.3f}, "
            f"Biomasa antesis={resultado['Biomasa_Antesis_Sim']:.3f} kg/ha, "
            f"Biomasa total={resultado['Biomasa_Total_Sim']:.3f} kg/ha, "
            f"HI={resultado['HI_penalizado']:.4f}"
        )


if __name__ == "__main__":
    main()
