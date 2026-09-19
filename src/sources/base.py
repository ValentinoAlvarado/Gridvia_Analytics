"""
sources/base.py — Clase base para las fuentes de datos.

Define la interfaz comun que comparten todas las fuentes (COES, ERA5, fichas).
Patron Strategy: cada fuente concreta implementa descargar() a su manera,
pero todas se usan igual desde el pipeline.
"""

from abc import ABC, abstractmethod
from pathlib import Path
import pandas as pd


class DataSource(ABC):
    """Interfaz base de una fuente de datos descargable."""

    def __init__(self, raw_dir: str):
        # Carpeta donde se guardan/leen los datos crudos (cache).
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def descargar(self) -> pd.DataFrame:
        """Descarga (o lee de cache) y devuelve los datos como DataFrame."""
        ...

    def _existe_cache(self, nombre: str, min_bytes: int = 2000) -> bool:
        """True si ya existe el archivo en cache (evita re-descargar)."""
        f = self.raw_dir / nombre
        return f.exists() and f.stat().st_size > min_bytes