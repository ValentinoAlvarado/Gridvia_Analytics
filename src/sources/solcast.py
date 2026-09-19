"""
Descarga de irradiancia Solcast a 15 min (experimento exp02_solcast_15min).

Esta fuente NO está aún en el notebook: es el plan para recuperar la
granularidad de 15 min en el lado meteorológico, que se pierde al
resamplear COES a 1h en exp01.

Solcast es nativo 15min y sale 15min: no se resamplea.
Cuando se combine con COES en exp02, COES se instancia con
output_resolution="15min" (sin resamplear).
"""
from __future__ import annotations
import pandas as pd
from .base import DataSource


class SolcastDownloader(DataSource):

    native_resolution = "15min"
    output_resolution = "15min"

    def __init__(self, cfg):
        super().__init__(cfg)
        # TODO: endpoint y api key de Solcast (agregar a fuentes.yaml)

    def download(self) -> pd.DataFrame:
        """GET histórico Solcast por planta (lat/lon), 15min."""
        ...

    def validate(self) -> None:
        ...

    def _is_cached(self) -> bool:
        return False
