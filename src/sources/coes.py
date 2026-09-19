"""
sources/coes.py — Descarga de mediciones de generacion solar del COES.

Migrado de las celdas 4, 6, 8, 10 del notebook original.
Descarga mensual reanudable (con cache: no re-descarga meses ya presentes).

Uso:
    coes = COESDownloader(raw_dir="data/raw/coes_csv")
    coes.descargar()            # descarga todos los meses faltantes
    df = coes.consolidar()      # devuelve el DataFrame 'largo' (celda 12)
"""

import os
import glob
import re
import time
import calendar
import unicodedata
import requests
import pandas as pd

from .base import DataSource


# --- Configuracion (celda 4) -----------------------------------------------
BASE_URL = "https://www.coes.org.pe/Portal/mediciones/medidoresgeneracion"

# Lista de empresas/medidores del COES (celda 4)
EMPRESAS = (
    "14260,69,15214,11772,12439,11777,10481,12056,12362,13196,12896,10628,15707,"
    "10420,12708,13165,10901,15571,12584,11095,17,11153,58,19,10684,30,27,40,11228,23,24,2,"
    "11389,11129,14173,11412,206,11544,11058,12097,10552,11429,12884,15624,15392,10725,11527,"
    "10647,14973,11981,11840,11841,12974,10974,11258,11644,11444,11940,12364,11149,11528,12634,"
    "12624,13726,12479,14807,11185,13,10916,13965,67,108,11217,12480,15259,11102,13120,11218,"
    "11063,149,11323,13966,15009,61,10913,10587,8,138,12758,11103,15080,10,15683,14342,13984,"
    "167,10422,180,11146,15014,4,5,9,76,11563,10636,11509,12096,11395,13783,18,48,10582,11064,"
    "47,11100,10755,12190,11053,10984,11101,11486,6,11567,10767,11894"
)

# Mapeo de nombres de circuito COES -> nombre de planta unificado (celda 12)
MAPEO = {
    "RUBI_CIRCUITO_1-5": "RUBI", "RUBI_CIRCUITO_6-10": "RUBI",
    "GTSMAJES": "MAJES", "MOQUEGUA_SOLAR": "MOQUEGUA_FV",
    "PANAM_SOLAR": "PANAMERICANA", "GTSREPAR": "REPARTICION",
    "TACNA_SOLAR": "TACNA", "YARUCAYA": "YARUCAYA",
    "INTIPAMPA_SOLAR": "INTIPAMPA", "EXPANSION_INTIPAMPA": "EXPANSION_INTIPAMPA",
    "COENERGY": "COENERGY", "MATARANI": "MATARANI",
    "SAN_MARTIN_SOLAR-BL1": "SAN_MARTIN", "SAN_MARTIN_SOLAR-BL2": "SAN_MARTIN",
    "SUNNY-BL1": "SUNNY", "SUNNY-BL2": "SUNNY",
    "SUNNY_EXPANSION-BL1": "SUNNY_EXPANSION", "SUNNY_EXPANSION-BL2": "SUNNY_EXPANSION",
    "CARHUAQUERO_CS": "CARHUAQUERO", "CLEMESI": "CLEMESI",
}


class COESDownloader(DataSource):
    """Descarga y consolida las mediciones de generacion solar del COES."""

    def __init__(self, raw_dir: str = "data/raw/coes_csv",
                 anio_ini: int = 2018, mes_ini: int = 1,
                 anio_fin: int = 2026, mes_fin: int = 5):
        super().__init__(raw_dir)
        self.anio_ini, self.mes_ini = anio_ini, mes_ini
        self.anio_fin, self.mes_fin = anio_fin, mes_fin

    # --- Sesion y peticiones (celda 6) -------------------------------------
    def _make_session(self):
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://www.coes.org.pe", "Referer": BASE_URL,
            "X-Requested-With": "XMLHttpRequest",
        })
        if os.path.exists("cookie.txt"):
            ck = open("cookie.txt", encoding="utf-8").read().strip()
            if ck:
                s.headers["Cookie"] = ck
        s.get(BASE_URL, timeout=60)
        return s

    def _payload(self, fi, ff):
        return {"fechaInicial": fi, "fechaFinal": ff, "empresas": EMPRESAS,
                "tiposGeneracion": "3", "central": "1", "parametros": "1", "tipo": "3"}

    def _es_csv(self, r):
        ct = r.headers.get("Content-Type", "").lower()
        return (r.status_code == 200 and len(r.content) > 2000
                and ("csv" in ct or "text" in ct or "octet" in ct))

    def _bajar_mes(self, s, fi, ff):
        form = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        s.post(BASE_URL + "/validarexportacion", headers=form, data=self._payload(fi, ff), timeout=120)
        s.post(BASE_URL + "/exportar", headers=form, data=self._payload(fi, ff), timeout=120)
        return s.get(BASE_URL + "/descargar", params={"tipo": "3"}, timeout=120)

    # --- Descarga masiva reanudable (celda 10) -----------------------------
    def descargar(self):
        """Descarga todos los meses del rango que no esten ya en cache."""
        s = self._make_session()
        y, m = self.anio_ini, self.mes_ini
        while (y, m) <= (self.anio_fin, self.mes_fin):
            nombre = f"solar_{y}_{m:02d}.csv"
            if self._existe_cache(nombre):
                print(f"  {y}-{m:02d}  existe, salto")
            else:
                ult = calendar.monthrange(y, m)[1]
                try:
                    r = self._bajar_mes(s, f"01/{m:02d}/{y}", f"{ult:02d}/{m:02d}/{y}")
                    if self._es_csv(r):
                        (self.raw_dir / nombre).write_bytes(r.content)
                        print(f"  {y}-{m:02d}  OK ({len(r.content)//1024} KB)")
                    else:
                        print(f"  {y}-{m:02d}  FALLO ({r.status_code}) -> renuevo sesion")
                        s = self._make_session()
                except Exception as e:
                    print(f"  {y}-{m:02d}  ERROR {e}")
                time.sleep(2.5)
            m += 1
            if m > 12:
                m = 1; y += 1
        print("Listo:", self.raw_dir)
        return self

    # --- Consolidacion a formato largo (celda 12) --------------------------
    @staticmethod
    def _normalizar_etiqueta(col):
        p = col.split(" -", 1)[-1].strip().upper()
        p = "".join(c for c in unicodedata.normalize("NFD", p)
                    if unicodedata.category(c) != "Mn")
        p = re.sub(r"\s+", "_", p)
        p = re.sub(r"_+", "_", p)
        return p

    def _leer_csv_mes(self, path):
        df = None
        for enc in ("utf-8", "latin-1"):
            try:
                df = pd.read_csv(path, encoding=enc, skipinitialspace=True); break
            except Exception:
                continue
        if df is None:
            raise IOError(path)
        df.columns = [c.strip() for c in df.columns]
        tcol = df.columns[0]
        df[tcol] = pd.to_datetime(df[tcol], dayfirst=True, errors="coerce")
        df = df[df[tcol].notna()].set_index(tcol); df.index.name = "timestamp"
        salida = {}
        for col in df.columns:
            c = MAPEO.get(self._normalizar_etiqueta(col))
            if c is None:
                continue
            serie = pd.to_numeric(df[col], errors="coerce")
            salida[c] = (salida[c] + serie) if c in salida else serie
        return pd.DataFrame(salida)

    def consolidar(self) -> pd.DataFrame:
        """Lee todos los CSV y devuelve el DataFrame en formato largo."""
        archivos = sorted(glob.glob(str(self.raw_dir / "*.csv")))
        print(f"Leyendo {len(archivos)} archivos...")
        partes = [self._leer_csv_mes(a) for a in archivos]
        full = pd.concat(partes).sort_index()
        full = full[~full.index.duplicated(keep="first")]
        ancho = full.resample("1h", label="right", closed="right").mean()
        largo = (ancho.reset_index()
                      .melt(id_vars="timestamp", var_name="item_id", value_name="potencia_mw"))
        return largo