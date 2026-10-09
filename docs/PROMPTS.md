🚀 MASTER PROMPT: DESARROLLO DE UN MODELO HÍBRIDO BIOFÍSICO-MACHINE LEARNING PARA LA PREDICCIÓN DE RENDIMIENTO DE CEBADA (RETO AGROCEBADA FIRA 2026)

1. CONTEXTO GENERAL Y OBJETIVO DEL PROYECTO
    Reto: Predecir con máxima precisión, interpretabilidad y sustento agronómico el rendimiento de cebada ($ton/ha$) para 59 parcelas de evaluación a partir de un conjunto de entrenamiento de 138 parcelas con rendimiento conocido en el Altiplano Central mexicano (Hidalgo, Puebla y Tlaxcala).
    Ciclo Agrícola: Abril - Octubre 2025.
    Filosofía del Enfoque: Implementar una arquitectura Híbrida PBM-informed ML (Feature Engineering Biofísico + Machine Learning + Explicabilidad SHAP). En lugar de usar un simulador mecanicista rígido o un modelo de ML tipo "caja negra" basado solo en imágenes satelitales, se construirá un Simulador Biofísico Simplificado en Python para generar 12 variables sintéticas explicativas (estrés hídrico, biomasa teórica y fenología) que alimentarán a algoritmos de Gradient Boosting (XGBoost / CatBoost).
    
2. MAPEO DE INSUMOS Y FUENTES DE DATOS
    A. Datos Disponibles en el Dataset Oficial
        Shapefile de Parcelas: Geometría exacta, coordenadas (Lat/Lon) en Hidalgo, Puebla y Tlaxcala.
        Topografía Estática: Elevación (m) y pendiente (%).
        Clima Mensual: Precipitación acumulada, $T_{min}$ y $T_{max}$ mensual.
        Índices Vegetativos Satelitales: Series temporales de Sentinel-2, Landsat (2022-2025) y Planet (2025) conteniendo NDVI, SAVI, EVI, LAI, fPAR e índices de estrés hídrico/residuos.
    B. Datos Complementarios a Extraer de Fuentes Públicas
        1. Serie Climatológica Diaria (NASA POWER API / ERA5-Land):
            Variables: $T_{max}$, $T_{min}$ ($^\circ C$), Precipitación diaria ($P_t$ en $mm$) y Radiación Solar Global ($R_s$ en $MJ/m^2/día$).
        2. Propiedades Hidráulicas del Suelo (SoilGrids250m / INIFAP):
            Variables: % Arcilla, % Arena, % Limo, Densidad aparente a $0-60\text{ cm}$.
            Derivación vía Ecuaciones de Pedotransferencia (Saxton & Rawls): Capacidad de Campo ($FC$), Punto de Marchitez Permanente ($PWP$) y Capacidad de Agua Disponible ($AWC = FC - PWP$).
        3. Parámetros Agronómicos Estándar (FAO-56 & Literatura CERES-Barley / APSIM):
            Coeficientes de cultivo: $Kc_{ini} = 0.30$, $Kc_{mid} = 1.15$, $Kc_{end} = 0.25$.
            Fracción de agotamiento sin estrés: $p = 0.55$.
            Temperatura base: $T_{base} = 0.0^\circ C \text{ a } 2.0^\circ C$.
            Umbrales térmicos: $GDD_{antesis\_target} = 800 \ ^\circ C\cdot d$, $GDD_{madurez\_target} = 1450 \ ^\circ C\cdot d$.
            Eficiencia de Uso de la Luz Máxima: $RUE_{max} = 1.2 \ g/MJ \text{ PAR}$.
            Índice de Cosecha Base: $HI_{base} = 0.42$.

3. ARQUITECTURA MODULAR DEL SIMULADOR BIOFÍSICO EN PYTHON
    El simulador se ejecutará paso a paso a escala diaria ($t = 1 \dots N$ días del ciclo) para cada parcela:

┌────────────────────────────────────────────────────────────────────────┐
│ MÓDULO 1: CLIMA E INTERPOLACIÓN                                        │
│ ├─ Cálculo de Radiación Extraterrestre: Ra = f(Latitud, DOY)           │
│ ├─ Cálculo de PAR diario: PAR_t = 0.48 * R_s                           │
│ └─ Cálculo de ETo diaria (Hargreaves-Samani / FAO-56):                  │
│    ETo_t = 0.0023 * (T_media + 17.8) * sqrt(Tmax - Tmin) * Ra          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ MÓDULO 2: FENOLOGÍA BASADA EN TIEMPO TÉRMICO (GDD)                    │
│ ├─ Acumulación diaria: GDD_t = GDD_{t-1} + max(0, T_media - T_base)    │
│ └─ Identificación de estadios:                                         │
│    - Vegetativo : 0 <= GDD < GDD_antesis                               │
│    - Antesis    : Ventana de +/- 10 días alrededor de GDD_antesis      │
│    - Llenado    : GDD_antesis <= GDD < GDD_madurez                     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ MÓDULO 3: BALANCE HÍDRICO EN 1D (BUCKET MODEL)                        │
│ ├─ Actualización del depósito: SW_t = max(PWP, min(FC, SW_{t-1} + P_t - ETa_t))│
│ ├─ Coeficiente de Estrés Hídrico (KS_t):                               │
│    Si SW_t >= (FC - p*AWC) -> KS_t = 1.0                              │
│    Si SW_t <  (FC - p*AWC) -> KS_t = (SW_t - PWP) / ((1 - p) * AWC)    │
│ └─ Evapotranspiración Real: ETa_t = ETo_t * Kc_t * KS_t               │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ MÓDULO 4: MONTEITH LUE + ASIMILACIÓN SATELITAL                        │
│ ├─ Interp. diaria de fPAR_t desde NDVI satelital (Planet/Sentinel-2)   │
│ ├─ Incremental de Biomasa: dBIO_t = PAR_t * fPAR_t * RUE_max * KS_t    │
│ ├─ Biomasa Acumulada: BIO_t = BIO_{t-1} + dBIO_t                       │
│ └─ Ajuste de Índice de Cosecha: HI_penalizado = HI_base * f(KS_llenado)│
└────────────────────────────────────────────────────────────────────────┘

4. MATRIZ DE LAS 12 VARIABLES BIOFÍSICAS SINTÉTICAS GENERADAS
    Cada parcela del dataset se enriquecerá con las siguientes 12 variables biofísicas calculadas por el simulador:
        1. GDD_antesis: Tiempo térmico acumulado hasta la fecha de floración simulada ($^\circ C \cdot d$).
        2. GDD_llenado: Tiempo térmico acumulado durante el periodo de llenado de grano ($^\circ C \cdot d$).
        3. DAP_antesis_est: Días después de la siembra estimados para alcanzar la antesis.
        4. ETo_acum: Demanda atmosférica total de agua en el ciclo ($mm$).
        5. ETa_acum: Evapotranspiración real consumida por el cultivo ($mm$).
        6. Deficit_Hidrico_Total: Sequía o brecha hídrica acumulada ($ETo\_acum - ETa\_acum$ en $mm$).
        7. KS_prom_antesis: Promedio del coeficiente de estrés hídrico (0 a 1) en la ventana crítica de floración ($\pm 10$ días).
        8. KS_prom_llenado: Promedio del coeficiente de estrés hídrico (0 a 1) durante la fase de llenado de grano.
        9. fPAR_integrado: Capacidad fotosintética integral observada por satélite (área bajo la curva $fPAR - t$).10. Biomasa_Antesis_Sim: Biomasa seca vegetal acumulada a la floración ($kg/ha$).
        11. Biomasa_Total_Sim: Biomasa seca total simulada a madurez ($kg/ha$).
        12. HI_penalizado: Índice de cosecha base penalizado por el estrés hídrico en llenado.
        
5. PIPELINE DE INTEGRACIÓN CON MACHINE LEARNING
┌────────────────────────────────────────────────────────────────────────┐
│ CONSOLIDACIÓN DEL DATAFRAME FINAL                                      │
│ [ Variables Topográficas ] + [ Índices Satelitales ] + [ 12 Variables Biofísicas ]
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ ENTRENAMIENTO DE MODELOS ENSAMBLE (XGBoost / CatBoost / LightGBM)      │
│ ├─ Estrategia de Validación: Repeated GroupKFold por región/parcela    │
│ ├─ Optimización de Hiperparámetros: Bayesian Optimization (Optuna)     │
│ └─ Métrica de Evaluación: RMSE, MAE y R² en las 138 parcelas de train  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PREDICCIÓN Y GENERACIÓN DE ENTREGABLES                                 │
│ ├─ Predicción de rendimiento (ton/ha) para las 59 parcelas de test     │
│ └─ Análisis de Explicabilidad con SHAP Values                          │
└────────────────────────────────────────────────────────────────────────┘

6. ESTRATEGIA DE EXPLICABILIDAD Y DIAGNÓSTICO CON SHAP VALUES
    Para justificar el valor científico del modelo ante el jurado, se aplicará SHAP (SHapley Additive exPlanations) sobre la predicción final de cada parcela:
    Ecuación de Descomposición Additiva: $$\hat{Y}_{\text{parcela}} = \bar{Y}_{\text{global}} + \sum_{j=1}^{M} \text{SHAP}_j$$
    Visualizaciones a Producir:
        1. SHAP Summary Beeswarm Plot: Demostrar el ranking global de importancia de características, probando que variables biofísicas como KS_prom_antesis y Biomasa_Total_Sim dominan la predicción por encima de índices vegetativos aislados.
        2. SHAP Waterfall / Force Plots por Parcela: Explicar diagnósticos individuales en parcelas de evaluación (por ejemplo: "La parcela X obtuvo una reducción de -0.7 ton/ha debido a un bajo KS_prom_llenado provocado por sequía terminal en septiembre").