"""
Consolidación de los CSV mensuales de COES en un DataFrame largo único.

Migra desde:
  - Celda 12 : MAPEO, normalizar_etiqueta(), leer_csv_mes(),
               y la fusión a formato largo (item_id, timestamp, potencia_mw).

El MAPEO de nombres crudos -> canónicos vive aquí como atributo de clase
porque es conocimiento de dominio propio de la consolidación.
"""
from __future__ import annotations
import re, unicodedata, glob
from pathlib import Path
import pandas as pd


class PlantConsolidator:

    # celda 12: dict completo de nombres crudos -> canónicos
    MAPEO = {
        "RUBI_CIRCUITO_1-5":    "RUBI",
        "RUBI_CIRCUITO_6-10":   "RUBI",
        "GTSMAJES":             "MAJES",
        "MOQUEGUA_SOLAR":       "MOQUEGUA_FV",
        "PANAM_SOLAR":          "PANAMERICANA",
        "GTSREPAR":             "REPARTICION",
        "TACNA_SOLAR":          "TACNA",
        "YARUCAYA":             "YARUCAYA",
        "INTIPAMPA_SOLAR":      "INTIPAMPA",
        "EXPANSION_INTIPAMPA":  "EXPANSION_INTIPAMPA",
        "COENERGY":             "COENERGY",
        "MATARANI":             "MATARANI",
        "SAN_MARTIN_SOLAR-BL1": "SAN_MARTIN",
        "SAN_MARTIN_SOLAR-BL2": "SAN_MARTIN",
        "SUNNY-BL1":            "SUNNY",
        "SUNNY-BL2":            "SUNNY",
        "SUNNY_EXPANSION-BL1":  "SUNNY_EXPANSION",
        "SUNNY_EXPANSION-BL2":  "SUNNY_EXPANSION",
        "CARHUAQUERO_CS":       "CARHUAQUERO",
        "CLEMESI":              "CLEMESI",
    }

    def __init__(self, cfg):
        self.cfg = cfg
        self.raw_dir = cfg.path("coes_csv")

    @staticmethod
    def _normalizar_etiqueta(col: str) -> str:
        """Mayúsculas, sin tildes, espacios->_. (celda 12)"""
        p = col.split(" -", 1)[-1].strip().upper()
        p = "".join(c for c in unicodedata.normalize("NFD", p)
                    if unicodedata.category(c) != "Mn")
        p = re.sub(r"\s+", "_", p)
        p = re.sub(r"_+", "_", p)
        return p

    def _leer_csv_mes(self, path) -> pd.DataFrame:
        """Lectura robusta utf-8/latin-1. (celda 12)"""
        ...

    def consolidate(self) -> pd.DataFrame:
        """
        Devuelve `largo`: DataFrame [item_id, timestamp, potencia_mw]
        con nombres canónicos aplicados vía MAPEO.
        """
        ...
