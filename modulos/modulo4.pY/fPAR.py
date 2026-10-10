import pandas as pd
import matplotlib.pyplot as plt

# 1. Cargar el archivo CSV
# Ajusta la ruta si tu script está en otra carpeta (ej. './data/processed/Datos para fpar.csv')
ruta_csv = '././data/processed/Datos para fpar.csv'

try:
    df = pd.read_csv(ruta_csv)
    print("¡Archivo cargado con éxito!")
    print(df.head())
except FileNotFoundError:
    print(f"⚠️ No se encontró el archivo en: {ruta_csv}. Revisa la ruta.")

# 2. Procesar las columnas de fecha y fPAR promedio
if 'df' in locals() and not df.empty:
    # NOTA: Si tu columna de fecha se llama diferente (ej. 'fecha', 'fecha_captura', 'date'), 
    # cambia 'fecha' en la siguiente línea por el nombre exacto que tenga en tu CSV.
    columna_fecha = 'fecha_captura' 
    columna_fpar = 'fapar_promedio'
    
    if columna_fecha in df.columns and columna_fpar in df.columns:
        # Convertir la columna de fecha a formato datetime de pandas para ordenarlas bien
        df[columna_fecha] = pd.to_datetime(df[columna_fecha], format="%d/%m/%Y")
        
        # Ordenar cronológicamente por fecha
        df = df.sort_values(by=columna_fecha)
        
        # Rellenar valores nulos si los hubiera con interpolación
        df[columna_fpar] = df[columna_fpar].interpolate().fillna(0)
        
        # 3. Graficar la evolución temporal del fPAR Promedio
        plt.figure(figsize=(10, 5))
        plt.plot(df[columna_fecha], df[columna_fpar], color='#27ae60', linewidth=2, marker='o', markersize=4, label='fPAR Promedio')
        
        plt.title('Evolución Temporal del fPAR Promedio - Reto FIRA', fontsize=12, fontweight='bold')
        plt.xlabel('Fecha de Captura', fontsize=10)
        plt.ylabel('fPAR Promedio', fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()
        
    else:
        print("⚠️ Revisa los nombres de tus columnas. Columnas disponibles en el CSV:")
        print(df.columns.tolist())