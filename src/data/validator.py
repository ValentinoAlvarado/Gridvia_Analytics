"""
Unificación potencia+meteo y validación de integridad temporal.

Migra desde:
  - Celda 21/22 : merge de potencia (largo) con meteo (largo_meteo)
                  -> largo_unificado, e inspección de alineación
  - Celda 27    : verificación de rejilla horaria (gaps, duplicados, déficit)

Es la última puerta antes del modelado: si pasa, largo_unificado está
listo para TimeSeriesPredictor.
"""
from __future__ import annotations
import pandas as pd


class TemporalValidator:

    def __init__(self, freq: str = "1h"):
        self.freq = freq

    def unify(self, largo: pd.DataFrame, largo_meteo: pd.DataFrame) -> pd.DataFrame:
        """Merge potencia + covariables meteo por (item_id, timestamp). (celda 22)"""
        ...

    def validate(self, largo_unificado: pd.DataFrame) -> pd.DataFrame:
        """
        Verifica por planta: gaps temporales, duplicados, déficit de rejilla.
        Lanza si hay problemas. Devuelve el mismo df si todo OK. (celda 27)
        """
        ...
        return largo_unificado
