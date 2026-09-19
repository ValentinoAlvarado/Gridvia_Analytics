"""
Diagrama de Taylor (sigma, R, cRMSD) por modelo.

Migra desde:
  - Celda 46/47 : SmartPersistence baseline acotado al universo del WF
  - Celda 48    : stats_taylor_por_planta(), construcción de df_taylor
  - Celda 49    : render del diagrama agregado (skill_metrics)
  - Celda 50    : sanity check de coordenadas
  - Celda 51    : diagramas de Taylor por planta
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .base import Evaluator


class TaylorDiagram(Evaluator):

    @staticmethod
    def _stats_por_planta(y_true, y_pred):
        """sigma_pred, R (Pearson), cRMSD. (celda 48)"""
        ...

    def _build_df_taylor(self, df_preds) -> pd.DataFrame:
        """Agrega por mediana entre plantas + SmartPersistence. (celda 48)"""
        ...

    def evaluate(self) -> None:
        """Render del Taylor agregado y por planta. (celdas 49, 51)"""
        ...
