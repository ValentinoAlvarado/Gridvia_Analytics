"""
Análisis SHAP sobre el booster LightGBM q=0.5 de DirectTabular.

Migra desde:
  - Celdas 53-56 : navegación al booster interno (DirectTabular ->
                   most_recent_model -> tabular -> LGBModel -> q50)
  - Celda 57     : reconstrucción de feature matrix (lags) + SHAP values

Aísla covariables meteorológicas del resto de features (lags).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from .base import Evaluator


class ShapAnalyzer(Evaluator):

    def __init__(self, cfg, df_static, largo_unificado):
        super().__init__(cfg, df_static)
        self.largo = largo_unificado            # necesita la serie para los lags
        self.lags = cfg["modelo"]["shap"]["lags"]
        self.fit_dir = cfg.path("models") / "walkforward_v1" / "fits"

    def _extract_booster(self):
        """Baja hasta el booster LightGBM q=0.5. (celdas 53-56)"""
        ...

    def _build_feature_matrix(self) -> pd.DataFrame:
        """Reconstruye lags + covariables igual que el entrenamiento. (celda 57)"""
        ...

    def evaluate(self) -> None:
        """Calcula SHAP y guarda bar + beeswarm. (celda 57)"""
        ...
