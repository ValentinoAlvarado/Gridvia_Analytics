"""
Clase base abstracta para evaluadores.

Patrón Strategy: todos reciben las predicciones del walk-forward y
producen figuras/tablas; difieren en el cálculo. Contrato uniforme.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
import pandas as pd


class Evaluator(ABC):
    def __init__(self, cfg, df_static: pd.DataFrame):
        self.cfg = cfg
        self.static = df_static
        self.pred_dir = cfg.path("models") / "walkforward_v1" / "preds"
        self.out_dir = cfg.path("figures")
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.quantiles = cfg["modelo"]["quantiles"]

    def _load_preds(self) -> pd.DataFrame:
        """Carga y concatena todos los parquet de preds. (celdas 43/58/59...)"""
        archivos = sorted(self.pred_dir.glob("*.parquet"))
        return pd.concat([pd.read_parquet(f) for f in archivos], ignore_index=True)

    @abstractmethod
    def evaluate(self) -> None:
        """Calcula y guarda la figura/tabla correspondiente."""
