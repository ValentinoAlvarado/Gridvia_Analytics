"""
GridviaPipeline — Facade que orquesta todo el flujo.

Es la única clase con la que habla el notebook. Mantiene el estado en
atributos (largo, largo_unificado, df_static) en vez de variables
globales. Cada método corresponde a una fase y devuelve self (fluent),
para poder encadenar: .descargar().consolidar().modelar().evaluar()
"""
from __future__ import annotations
from .config import Config

from .sources.coes import COESDownloader
from .sources.era5 import ERA5Downloader
from .sources.fichas import FichaDownloader

from .data.consolidator import PlantConsolidator
from .data.cleaner import PhysicalCleaner
from .data.validator import TemporalValidator
from .features.static import StaticFeatureBuilder

from .models.walkforward import WalkForwardRunner

from .evaluation.taylor import TaylorDiagram
from .evaluation.shap_analysis import ShapAnalyzer
from .evaluation.reports import MetricsReporter


class GridviaPipeline:

    def __init__(self, config_path: str = "conf/config.yaml"):
        self.cfg = Config.load(config_path)
        # estado del pipeline (antes: globales del notebook)
        self.coes = None
        self.era5 = None
        self.fichas = None
        self.largo = None
        self.df_static = None
        self.largo_unificado = None

    # ---- Fase 1: descarga (celdas 6-21, 30) ----
    def descargar(self) -> "GridviaPipeline":
        out_res = self.cfg["resolucion"]["coes_salida"]   # "1h" exp01
        self.coes   = COESDownloader(self.cfg, output_resolution=out_res).run()
        self.era5   = ERA5Downloader(self.cfg).run()
        self.fichas = FichaDownloader(self.cfg).run()
        return self

    # ---- Fase 2: consolidación + limpieza + validación (celdas 12-27) ----
    def consolidar(self) -> "GridviaPipeline":
        self.largo = PlantConsolidator(self.cfg).consolidate()
        self.df_static = StaticFeatureBuilder(self.cfg).build()

        nominal = self.df_static.set_index("item_id")["pot_inst_mw"].to_dict()
        cleaner = PhysicalCleaner(self.cfg, nominal)
        self.largo = cleaner.filter_inclusion(self.largo)

        validator = TemporalValidator(freq=self.cfg["resolucion"]["coes_salida"])
        unif = validator.unify(self.largo, self.era5)
        unif = cleaner.clean(unif)
        self.largo_unificado = validator.validate(unif)
        return self

    # ---- Fase 3: modelado (celdas 33-41) ----
    def modelar(self) -> "GridviaPipeline":
        WalkForwardRunner(self.cfg).run(self.largo_unificado, self.df_static)
        return self

    # ---- Fase 4: evaluación (celdas 43-64) ----
    def evaluar(self) -> "GridviaPipeline":
        TaylorDiagram(self.cfg, self.df_static).evaluate()
        ShapAnalyzer(self.cfg, self.df_static, self.largo_unificado).evaluate()
        MetricsReporter(self.cfg, self.df_static).evaluate()
        return self
