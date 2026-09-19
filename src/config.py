"""
Carga y unifica la configuración desde los archivos YAML de conf/.

Reemplaza todas las constantes globales dispersas en las celdas
(ANIO_INI, RAW_DIR, UMBRAL_GHI_ALTO, PREDICTION_LENGTH, etc.).
"""
from __future__ import annotations
from pathlib import Path
import yaml


class Config:
    """
    Acceso unificado a config.yaml + plantas.yaml + fuentes.yaml + modelo.yaml.

    Uso:
        cfg = Config.load("conf/config.yaml")
        cfg["periodo"]["inicio"]      -> "2018-01-01"
        cfg.plantas                   -> lista de dicts de plantas
        cfg.coords                    -> {item_id: (lat, lon)}
    """

    _EXTRAS = ("plantas", "fuentes", "modelo")

    def __init__(self, data: dict):
        self._data = data

    @classmethod
    def load(cls, path: str | Path = "conf/config.yaml") -> "Config":
        path = Path(path)
        base = yaml.safe_load(path.read_text(encoding="utf-8"))
        for extra in cls._EXTRAS:
            f = path.parent / f"{extra}.yaml"
            if f.exists():
                base[extra] = yaml.safe_load(f.read_text(encoding="utf-8"))
        return cls(base)

    # --- acceso genérico ---
    def __getitem__(self, key):
        return self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)

    # --- atajos de conveniencia ---
    @property
    def plantas(self) -> list[dict]:
        return self._data["plantas"]["plantas"]

    @property
    def coords(self) -> dict[str, tuple]:
        """{item_id: (lat, lon)} para las plantas con coordenadas."""
        return {
            p["item_id"]: (p["lat"], p["lon"])
            for p in self.plantas
            if p.get("lat") is not None
        }

    @property
    def item_ids(self) -> list[str]:
        return [p["item_id"] for p in self.plantas]

    def path(self, key: str) -> Path:
        """Devuelve un path de la sección paths como objeto Path."""
        return Path(self._data["paths"][key])
