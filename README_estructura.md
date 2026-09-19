# Gridvia Analytics — Estructura POO

Refactorización del notebook único (65 celdas) a arquitectura orientada a objetos
que satisface la prueba de fuego UML.

## Estructura

```
Gridvia_Analytics/
├── conf/                    # configuración (reemplaza constantes hardcodeadas)
│   ├── config.yaml          # periodo, paths, umbrales de limpieza, resoluciones
│   ├── plantas.yaml         # 11 plantas: lat, lon, fechas, nombre GIS
│   ├── fuentes.yaml         # endpoints COES/ERA5/GIS, IDs de ficha
│   └── modelo.yaml          # hiperparámetros walk-forward, quantiles, lags SHAP
│
├── src/
│   ├── config.py            # Config.load() — carga y unifica los YAML
│   ├── sources/             # DESCARGA (Template Method + Strategy)
│   │   ├── base.py          # DataSource (ABC): run(), download(), resoluciones
│   │   ├── coes.py          # COESDownloader   nativo 15min → salida 1h/15min
│   │   ├── era5.py          # ERA5Downloader   1h
│   │   ├── solcast.py       # SolcastDownloader 15min (exp02)
│   │   └── fichas.py        # FichaDownloader  static
│   ├── data/                # PROCESAMIENTO (Pipeline)
│   │   ├── consolidator.py  # PlantConsolidator (MAPEO, normalización)
│   │   ├── cleaner.py       # PhysicalCleaner (inclusión + P/GHI)
│   │   └── validator.py     # TemporalValidator (unify + integridad)
│   ├── features/
│   │   └── static.py        # StaticFeatureBuilder (GIS + fichas + elevación)
│   ├── models/
│   │   ├── metrics.py       # PearsonR
│   │   ├── baselines.py     # SmartPersistenceModelV2
│   │   └── walkforward.py   # WalkForwardRunner
│   ├── evaluation/          # EVALUACIÓN (Strategy)
│   │   ├── base.py          # Evaluator (ABC)
│   │   ├── taylor.py        # TaylorDiagram
│   │   ├── shap_analysis.py # ShapAnalyzer
│   │   └── reports.py       # MetricsReporter
│   └── pipeline.py          # GridviaPipeline (Facade)
│
└── main.ipynb               # orquestador: 5 líneas encadenadas
```

## Pasos de migración (celda → método)

El esqueleto está listo con firmas y docstrings. Para cada archivo, copia el
cuerpo de la celda indicada al método correspondiente. Orden recomendado:

1. **config.py** — ya funcional. Verifica que carga los 4 YAML.
2. **sources/coes.py** — celdas 6, 8, 10 → `_make_session`, `_bajar_mes`, `download`.
3. **sources/era5.py** — celdas 18-21 → `_descargar_planta_timeseries`, `_leer_era5_planta`, `download`.
4. **sources/fichas.py** — celda 30 → `_bajar_ficha`, `download`.
5. **data/consolidator.py** — celda 12 → `_leer_csv_mes`, `consolidate` (MAPEO ya está).
6. **features/static.py** — celdas 16, 31, 32 → `_fetch_gis`, `_parse_ficha`, `_obtener_elevacion`, `build`.
7. **data/cleaner.py** — celdas 14, 23, 24 → `filter_inclusion`, `_mark_puntual`, `_mark_dia_completo`.
8. **data/validator.py** — celdas 22, 27 → `unify`, `validate`.
9. **models/metrics.py** y **baselines.py** — celdas 38, 39 → copiar tal cual (ya son clases).
10. **models/walkforward.py** — celda 41 → `_tsdf`, `run`.
11. **evaluation/taylor.py** — celdas 46-51 → `_stats_por_planta`, `_build_df_taylor`, `evaluate`.
12. **evaluation/shap_analysis.py** — celdas 53-57 → `_extract_booster`, `_build_feature_matrix`, `evaluate`.
13. **evaluation/reports.py** — celdas 43, 58-64 → un método privado por figura.

## Regla de oro POO

- Constante que cambia entre experimentos → va a YAML, no al código.
- Estado compartido entre pasos → atributo de clase, no variable global.
- Si un método no aparece en ningún diagrama UML → probablemente sobra.
- Si una clase necesita más de un Sequence Diagram → divídela.

## Ejecución

```python
from src.pipeline import GridviaPipeline
pipe = GridviaPipeline("conf/config.yaml").descargar().consolidar().modelar().evaluar()
```
