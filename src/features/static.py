"""
Construcción de features estáticas por planta para AutoGluon.

Migra desde:
  - Celda 16 : tabla insumo meteo (lat/lon desde GIS OSINERGMIN, fechas)
  - Celda 31 : parseo de fichas COES (CENTRALES + COMPONENTE), canonización
  - Celda 32 : altitud vía Open-Elevation API

Produce df_static: [item_id, latitude, longitude, altitude_m,
pot_inst_mw, ...] listo como static_features_df.
"""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd


class StaticFeatureBuilder:

    def __init__(self, cfg):
        self.cfg = cfg
        self.fichas_dir = cfg.path("fichas")
        self.gis_url = cfg["fuentes"]["gis_osinergmin"]["url"]
        self.elev_url = cfg["fuentes"]["elevacion"]["url"]

    # ---- celda 16 ----
    def _fetch_gis(self) -> dict:
        """Lat/lon/potencia desde GIS OSINERGMIN. (celda 16)"""
        ...

    # ---- celda 31 ----
    @staticmethod
    def _norm(x): ...
    @staticmethod
    def _to_float(x): ...
    def _parse_ficha(self, item_id) -> dict:
        """Parsea hojas CENTRALES y COMPONENTE de un .xlsx. (celda 31)"""
        ...

    # ---- celda 32 ----
    def _obtener_elevacion(self, lat, lon, retry: int = 2):
        """Altitud vía Open-Elevation, con reintentos. (celda 32)"""
        ...

    def build(self) -> pd.DataFrame:
        """Ensambla df_static completo: GIS + fichas + elevación."""
        ...
