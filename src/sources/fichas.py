"""
Descarga de fichas técnicas COES (Excel) para features estáticas.

Migra desde:
  - Celda 30 : es_excel(), bajar_ficha() (flujo 2 pasos export -> download)

No es una serie temporal: resolución no aplica. Se modela como
DataSource por uniformidad, con resoluciones "static".
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from .base import DataSource


class FichaDownloader(DataSource):

    native_resolution = "static"
    output_resolution = "static"

    def __init__(self, cfg):
        super().__init__(cfg)
        self.base = cfg["fuentes"]["coes_fichas"]["base_url"]
        self.ids = cfg["fuentes"]["coes_fichas"]["ids"]
        self.out_dir = cfg.path("fichas")

    def _bajar_ficha(self, s, id_elemento):
        """POST ExportarFichaTecnica -> GET DescargarExcel. (celda 30)"""
        ...

    def download(self) -> pd.DataFrame:
        """Baja los .xlsx de las 11 plantas. Devuelve índice de archivos."""
        ...

    def validate(self) -> None:
        ...

    def _resample_if_needed(self, df):
        return df   # estático: nunca se resamplea
