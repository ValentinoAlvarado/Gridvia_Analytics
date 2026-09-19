"""
Limpieza física determinista de la serie de potencia.

Migra desde:
  - Celda 14 : filtro de inclusión por meses operativos (>=18 meses)
  - Celda 23 : marcado puntual (parada con sol / generación sin sol)
  - Celda 24 : marcado de paradas de DÍA COMPLETO (>=80% horas sol a ~0)

No elimina filas: pone potencia_mw a NaN para que AutoGluon trate esos
timestamps como faltantes. Los umbrales vienen de config.yaml (no hardcode).
"""
from __future__ import annotations
import pandas as pd


class PhysicalCleaner:

    def __init__(self, cfg, nominal: dict):
        lim = cfg["limpieza"]
        self.nominal = nominal               # {item_id: pot_inst_mw}
        self.umbral_gen   = lim["umbral_gen"]
        self.umbral_meses = lim["umbral_meses"]
        self.ghi_alto     = lim["ghi_alto"]
        self.ghi_cero     = lim["ghi_cero"]
        self.pct_nominal  = lim["pct_nominal_min"]
        self.pct_horas    = lim["pct_horas_min"]

    # ---- celda 14 ----
    def filter_inclusion(self, largo: pd.DataFrame) -> pd.DataFrame:
        """Descarta plantas con < umbral_meses de historia operativa."""
        ...

    # ---- celda 23 ----
    def _mark_puntual(self, df: pd.DataFrame) -> pd.DataFrame:
        """NaN donde (pot<1%nom & GHI alto) o (pot>=1%nom & GHI~0)."""
        ...

    # ---- celda 24 ----
    def _mark_dia_completo(self, df: pd.DataFrame) -> pd.DataFrame:
        """NaN al día entero si >=80% de horas con sol alto están a ~0."""
        ...

    def clean(self, largo_unificado: pd.DataFrame) -> pd.DataFrame:
        """Aplica ambos marcados. Devuelve la serie con NaN físicos."""
        df = self._mark_puntual(largo_unificado)
        df = self._mark_dia_completo(df)
        return df
