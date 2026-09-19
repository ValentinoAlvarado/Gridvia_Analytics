"""
sources/era5.py — Descarga y procesamiento de covariables meteorologicas ERA5-Land.

Migrado de las celdas 16, 18, 19, 20, 22 del notebook original.
Flujo:
  1. obtiene coordenadas de las plantas desde el GIS de OSINERGMIN (celda 16/18)
  2. descarga ERA5-Land timeseries por planta via CDS API (celda 19)
  3. parsea los .nc (que vienen como ZIP) y deriva variables fisicas (celda 22)

Uso:
    era5 = ERA5Downloader(project_dir=".")
    df_meteo_input = era5.tabla_insumo(largo)   # coords + rangos por planta
    era5.descargar(df_meteo_input)              # descarga los .nc
    largo_meteo = era5.procesar(df_meteo_input) # DataFrame de covariables
"""

import os
import io
import zipfile
import requests
import numpy as np
import pandas as pd

from .base import DataSource

UMBRAL_GEN = 0.05

# Nombre item_id -> nombre en el GIS de OSINERGMIN (celda 16)
NOMBRE_GIS = {
    "RUBI": "RUBI", "PANAMERICANA": "PANAMERICANA SOLAR", "TACNA": "TACNA SOLAR",
    "MAJES": "MAJES", "MOQUEGUA_FV": "MOQUEGUA SOLAR", "REPARTICION": "REPARTICION",
    "INTIPAMPA": "INTIPAMPA", "YARUCAYA": "YARUCAYA", "CLEMESI": "CLEMESÍ",
    "CARHUAQUERO": "CARHUAQUERO", "MATARANI": "MATARANI", "SAN_MARTIN": "SAN MARTIN SOLAR",
}

URL_GIS = ("https://gisem.osinergmin.gob.pe/serverosih/rest/services/"
           "Electricidad/ELECTRICIDAD/MapServer/11/query")

# Variables ERA5-Land a descargar (celda 19)
VARIABLES = [
    "surface_solar_radiation_downwards", "2m_temperature", "2m_dewpoint_temperature",
    "10m_u_component_of_wind", "10m_v_component_of_wind", "surface_pressure",
    "total_precipitation",
]


class ERA5Downloader(DataSource):
    """Descarga y procesa covariables meteorologicas ERA5-Land por planta."""

    def __init__(self, project_dir: str = "."):
        self.project_dir = os.path.abspath(project_dir)
        era5_dir = os.path.join(self.project_dir, "data", "raw", "era5_land")
        super().__init__(era5_dir)
        self.cdsapirc = os.path.join(self.project_dir, ".cdsapirc")

    # --- Coordenadas desde el GIS de OSINERGMIN (celda 16) -----------------
    def _consultar_gis(self):
        params = {
            "where": "TIPO_CENTRAL='CENTRAL SOLAR'",
            "outFields": "EMPRESA,NOMBRE,POT_INST,LATITUD,LONGITUD,PUEST_OPER",
            "returnGeometry": "false", "f": "json",
        }
        r = requests.get(URL_GIS, params=params, timeout=60)
        return {feat["attributes"]["NOMBRE"]: feat["attributes"]
                for feat in r.json()["features"]}

    def tabla_insumo(self, largo: pd.DataFrame) -> pd.DataFrame:
        """Construye la tabla de coords + rangos temporales por planta (celda 16)."""
        gis = self._consultar_gis()
        filas = []
        for item_id in sorted(largo.item_id.unique()):
            g = largo[largo.item_id == item_id].sort_values("timestamp")
            inicio_csv, fin_csv = g["timestamp"].min(), g["timestamp"].max()
            g_real = g[g.potencia_mw > UMBRAL_GEN]
            inicio_real = g_real["timestamp"].min() if len(g_real) else pd.NaT
            fin_real = g_real["timestamp"].max() if len(g_real) else pd.NaT

            nombre_gis = NOMBRE_GIS.get(item_id)
            if nombre_gis is None or nombre_gis not in gis:
                print(f"AVISO: {item_id} sin coordenada en GIS"); continue
            info = gis[nombre_gis]
            filas.append({
                "item_id": item_id, "lat": info["LATITUD"], "lon": info["LONGITUD"],
                "pot_inst_mw": info["POT_INST"],
                "inicio_csv": inicio_csv, "fin_csv": fin_csv,
                "inicio_real": inicio_real, "fin_real": fin_real,
            })
        return pd.DataFrame(filas).sort_values("item_id").reset_index(drop=True)

    # --- Descarga ERA5-Land timeseries (celda 19) --------------------------
    def _cargar_credenciales(self):
        creds = {}
        with open(self.cdsapirc) as f:
            for linea in f:
                if ":" not in linea:
                    continue
                k, _, v = linea.partition(":")
                creds[k.strip()] = v.strip()
        return creds.get("url"), creds.get("key")

    def descargar(self, df_meteo_input: pd.DataFrame):
        """Descarga los .nc de ERA5-Land para cada planta (reanudable)."""
        import cdsapi
        url, key = self._cargar_credenciales()
        if not (url and key):
            raise RuntimeError(f"No se pudo leer credenciales de {self.cdsapirc}")
        client = cdsapi.Client(url=url, key=key)

        for _, fila in df_meteo_input.iterrows():
            item_id = fila["item_id"]
            out_path = os.path.join(self.raw_dir, f"{item_id}.nc")
            if os.path.exists(out_path) and os.path.getsize(out_path) > 10_000:
                print(f"  {item_id:14}  ya existe, salto"); continue
            inicio, fin = fila["inicio_csv"], fila["fin_csv"]
            rango = f"{inicio.strftime('%Y-%m-%d')}/{fin.strftime('%Y-%m-%d')}"
            print(f"  {item_id:14}  pidiendo ({rango})...")
            try:
                client.retrieve(
                    "reanalysis-era5-land-timeseries",
                    {"variable": VARIABLES,
                     "location": {"longitude": fila["lon"], "latitude": fila["lat"]},
                     "date": [rango], "data_format": "netcdf"},
                    out_path,
                )
                print(f"  {item_id:14}  OK")
            except Exception as e:
                print(f"  {item_id:14}  ERROR: {e}")
                if os.path.exists(out_path):
                    os.remove(out_path)
        return self

    # --- Parseo de ZIPs y derivacion de variables fisicas (celda 22) -------
    def _leer_era5_planta(self, item_id):
        import xarray as xr
        zip_path = os.path.join(self.raw_dir, f"{item_id}.nc")
        if not os.path.exists(zip_path):
            print(f"  {item_id:14}  no encontrado, salto"); return None
        datasets = []
        # Los .nc de ERA5-Land timeseries vienen comprimidos como ZIP
        with zipfile.ZipFile(zip_path, "r") as zf:
            for nombre in zf.namelist():
                raw = zf.read(nombre)
                datasets.append(xr.open_dataset(io.BytesIO(raw), engine="h5netcdf"))
        ds = xr.merge(datasets)
        df = ds.to_dataframe().reset_index().rename(columns={"valid_time": "timestamp"})
        for col in ["latitude", "longitude", "number", "expver"]:
            if col in df.columns:
                df = df.drop(columns=col)
        df["item_id"] = item_id
        return df.sort_values("timestamp").reset_index(drop=True)

    def procesar(self, df_meteo_input: pd.DataFrame) -> pd.DataFrame:
        """Parsea los .nc, deriva variables fisicas y corrige a hora local."""
        piezas = []
        for item_id in df_meteo_input["item_id"]:
            df_p = self._leer_era5_planta(item_id)
            if df_p is not None:
                piezas.append(df_p)
        m = pd.concat(piezas, ignore_index=True)

        # Derivar variables fisicas de las crudas de ERA5
        m["ghi"] = m["ssrd"] / 3600.0
        m["t_air"] = m["t2m"] - 273.15
        m["dewpoint"] = m["d2m"] - 273.15
        a, b = 17.625, 243.04
        Td, T = m["dewpoint"], m["t_air"]
        m["hr"] = 100.0 * np.exp((a*Td)/(b+Td)) / np.exp((a*T)/(b+T))
        m["wind_speed"] = np.sqrt(m["u10"]**2 + m["v10"]**2)
        m["pressure"] = m["sp"] / 100.0
        m["precip_mm"] = m["tp"] * 1000.0

        m = m[["timestamp", "item_id", "ghi", "t_air", "hr",
               "wind_speed", "pressure", "precip_mm"]]
        # Correccion UTC -> hora local Peru (UTC-5)
        m["timestamp"] = m["timestamp"] - pd.Timedelta(hours=5)
        return m