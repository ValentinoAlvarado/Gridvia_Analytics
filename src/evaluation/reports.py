"""
Reportes de métricas y figuras de desempeño.

Migra desde:
  - Celda 43/44 : evaluación honesta (nMAE, nRMSE, WQL, SQL) + leaderboard
  - Celda 58    : predicción de un día completo por modelo
  - Celda 59    : reliability diagram (calibración cuantílica)
  - Celda 60    : error por hora del día (nMAE)
  - Celda 61    : heatmap nMAE modelos × plantas
  - Celda 62/63 : nMAE por régimen de nubosidad (TCC)
  - Celda 64    : exportación de tablas a PNG

Agrupa todas las figuras de desempeño bajo un solo evaluador, cada una
en su propio método. Si crece demasiado, dividir en sub-evaluadores.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from .base import Evaluator


class MetricsReporter(Evaluator):

    def _leaderboard(self, df_preds) -> pd.DataFrame:
        """nMAE/nRMSE/WQL/SQL por modelo y planta. (celda 43)"""
        ...

    def _reliability(self, df_preds): ...      # celda 59
    def _error_por_hora(self, df_preds): ...   # celda 60
    def _heatmap_nmae(self, df_preds): ...      # celda 61
    def _por_nubosidad(self, df_preds): ...     # celda 63
    def _dia_ejemplo(self, df_preds): ...       # celda 58

    def evaluate(self) -> None:
        """Genera todas las figuras de desempeño en out_dir."""
        df = self._load_preds()
        self._leaderboard(df)
        self._reliability(df)
        self._error_por_hora(df)
        self._heatmap_nmae(df)
        self._por_nubosidad(df)
        self._dia_ejemplo(df)
