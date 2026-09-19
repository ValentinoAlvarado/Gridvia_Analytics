"""
MBCn v2 — Corrección de sesgo multivariada ERA5-Land -> Open-Meteo NWP.
Adaptado al formato real del pipeline Gridvia (DataFrames por planta).

Cambios vs v1:
  - Opera sobre pd.DataFrame con columnas del notebook: ghi, t_air, hr,
    wind_speed, pressure  (precip_mm EXCLUIDA: SHAP ~0 e intermitente).
  - Un mapeo POR PLANTA (el sesgo Open-Meteo<->ERA5 es local a cada lat/lon).
  - GHI condicionado por hora del día (banda horaria): el sesgo del GHI no es
    constante; es la covariable dominante en SHAP, así que se corrige por hora.
  - Filtro diurno (ghi>0) para el GHI antes de ajustar CDFs.
  - Carga de datos real: ERA5 desde largo_unificado; Open-Meteo desde CSV/parquet
    de la Historical Forecast API.
  - Validación: KS por variable antes/después + correlaciones cruzadas
    (prueba de que MBCn preserva la dependencia que el univariado rompe).

Ref: Cannon (2018), Climate Dynamics 50, 31-49.
"""

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

# Covariables corregidas — LAS SEIS que consume el modelo (precip_mm incluida).
# precip_mm recibe tratamiento de intermitencia (ceros) antes del MBCn multivariado,
# porque el modelo la usa como input aunque su SHAP sea bajo, y excluirla del vector
# alteraría la rotación de todas las demás.
COVARS = ["ghi", "t_air", "hr", "wind_speed", "pressure", "precip_mm"]
INTERMITENTE = ["precip_mm"]   # variables con masa en cero (días secos)


# ----------------------------------------------------------------------
# QM univariado empírico (bloque base)
# ----------------------------------------------------------------------
def _qmap_1d(x, src_ref, tgt_ref, n_q=1001):
    q = np.linspace(0.0, 1.0, n_q)
    src_q = np.quantile(src_ref, q)
    tgt_q = np.quantile(tgt_ref, q)
    ranks = np.interp(x, src_q, q)          # rank bajo src
    return np.interp(ranks, q, tgt_q)        # valor en tgt a ese rank; clampa colas


# ----------------------------------------------------------------------
# Tratamiento de intermitencia para precipitación (frecuencia de ceros)
# ----------------------------------------------------------------------
def _corregir_frecuencia_seca(x_om, om_ref, era5_ref, umbral=0.1):
    """
    Corrige la frecuencia de días secos ANTES del quantile mapping.

    Problema: Open-Meteo y ERA5 difieren en la fracción de horas con precip~0.
    Si OM predice lluvia más seguido que ERA5, un QM directo sobre todo el
    vector deja demasiadas horas húmedas. Se ajusta el umbral de OM para que
    su frecuencia de ceros iguale a la de ERA5, y luego se mapea la intensidad
    solo sobre las horas húmedas (Cannon 2018, sec. sobre variables acotadas
    en cero; equivalente al frequency-adjustment de Themeßl 2012).

    umbral: mm por debajo del cual se considera 'seco' (traza).
    Devuelve x corregido en frecuencia (aún sin QM de intensidad).
    """
    # fracción seca objetivo (ERA5) y de la fuente (OM)
    p_dry_era5 = np.mean(era5_ref <= umbral)
    # cuantil de OM que reproduce esa fracción seca
    if p_dry_era5 <= 0:
        return np.where(x_om <= umbral, 0.0, x_om)
    thr_om = np.quantile(om_ref, p_dry_era5)     # todo <= thr_om se vuelve seco
    out = np.where(x_om <= thr_om, 0.0, x_om)
    return out


# ----------------------------------------------------------------------
# MBCn: fit sobre el solape, transform sobre operativo
# ----------------------------------------------------------------------
class MBCn:
    def __init__(self, n_iter=30, seed=0):
        self.n_iter, self.rng = n_iter, np.random.default_rng(seed)

    @staticmethod
    def _rot(d, rng):
        Q, R = np.linalg.qr(rng.standard_normal((d, d)))
        return Q * np.sign(np.diag(R))

    def fit(self, om_cal, era5_cal):
        om, er = np.asarray(om_cal, float), np.asarray(era5_cal, float)
        self.d = om.shape[1]
        self.mu_, self.sd_ = er.mean(0), er.std(0) + 1e-12
        self.om_cal_, self.era5_cal_ = om, er
        self.rots_ = [self._rot(self.d, self.rng) for _ in range(self.n_iter)]
        # corrección del propio solape (para validación KS)
        self._cal_corr_ = self.transform(om)
        return self

    def transform(self, om_oper):
        cur = (np.asarray(om_oper, float) - self.mu_) / self.sd_
        src = (self.om_cal_   - self.mu_) / self.sd_
        tgt = (self.era5_cal_ - self.mu_) / self.sd_
        for R in self.rots_:
            cur_r, src_r, tgt_r = cur @ R, src @ R, tgt @ R
            for j in range(self.d):
                cur_r[:, j] = _qmap_1d(cur_r[:, j], src_r[:, j], tgt_r[:, j])
                src_r[:, j] = _qmap_1d(src_r[:, j], src_r[:, j], tgt_r[:, j])
            cur, src = cur_r @ R.T, src_r @ R.T
        return cur * self.sd_ + self.mu_


# ----------------------------------------------------------------------
# Corrección por planta, con GHI condicionado por hora
# ----------------------------------------------------------------------
def corregir_planta(df_era5, df_om, n_iter=30, seed=1):
    """
    df_era5, df_om: DataFrames de UNA planta, indexados/alineados por timestamp,
    con columnas COVARS + 'hour' (0-23). Deben cubrir el MISMO período (solape).
    Devuelve: df_om_corregido (mismas filas), y dict de diagnóstico KS.
    """
    assert list(df_era5.index) == list(df_om.index), "timestamps no alineados"
    hour = df_om["hour"].values
    out = df_om[COVARS].copy()

    # --- PASO 0: corregir frecuencia de ceros en variables intermitentes ---
    # (precip): se ajusta ANTES del MBCn para que la fracción de horas secas
    # de Open-Meteo iguale la de ERA5. Sin esto, el QM sobre precip queda mal.
    df_om_adj = df_om.copy()
    for c in INTERMITENTE:
        if c in COVARS:
            df_om_adj[c] = _corregir_frecuencia_seca(
                df_om[c].values, df_om[c].values, df_era5[c].values)

    # --- variables no-GHI CONTINUAS: MBCn multivariado global ---
    novars_cont = [c for c in COVARS if c != "ghi" and c not in INTERMITENTE]
    m = MBCn(n_iter, seed).fit(df_om_adj[novars_cont].values,
                                df_era5[novars_cont].values)
    out[novars_cont] = m.transform(df_om_adj[novars_cont].values)

    # --- variables intermitentes (precip): frecuencia YA corregida (paso 0);
    #     ahora QM de INTENSIDAD solo sobre horas húmedas de cada distribución ---
    for c in INTERMITENTE:
        if c not in COVARS:
            continue
        x = df_om_adj[c].values.copy()             # ya con frecuencia seca corregida
        wet_out = x > 0
        om_wet   = df_om_adj[c].values[df_om_adj[c].values > 0]
        era5_wet = df_era5[c].values[df_era5[c].values > 0]
        if wet_out.sum() > 0 and len(om_wet) >= 20 and len(era5_wet) >= 20:
            x[wet_out] = _qmap_1d(x[wet_out], om_wet, era5_wet)
        out[c] = np.clip(x, 0, None)

    # --- GHI: MBCn por hora del día, solo horas diurnas ---
    # (GHI domina SHAP; su sesgo varía con la elevación solar)
    ghi_corr = df_om["ghi"].values.copy()
    for h in range(24):
        sel = (hour == h) & (df_era5["ghi"].values > 0) & (df_om["ghi"].values > 0)
        if sel.sum() < 50:            # muy pocos puntos diurnos a esa hora
            continue
        # GHI se corrige junto a las no-GHI CONTINUAS para preservar dependencia
        # (precip queda fuera de este bloque: su tratamiento es el de intermitencia)
        cols = ["ghi"] + novars_cont
        mh = MBCn(n_iter, seed).fit(df_om.loc[sel, cols].values,
                                     df_era5.loc[sel, cols].values)
        ghi_corr[sel] = mh.transform(df_om.loc[sel, cols].values)[:, 0]
    ghi_corr = np.clip(ghi_corr, 0, None)   # GHI >= 0
    out["ghi"] = ghi_corr

    # --- diagnóstico ---
    # Variables continuas: KS global antes/después.
    # Variables intermitentes (precip): NO se usa KS global (la masa de ceros lo
    # domina y lo hace no informativo). Se reporta en dos componentes:
    #   (a) error en frecuencia de horas secas   -> componente discreta
    #   (b) KS SOLO sobre horas húmedas           -> componente de intensidad
    diag = {}
    UMBRAL_HUMEDO = 0.1
    for c in COVARS:
        if c in INTERMITENTE:
            era5_v, om_v, cor_v = (df_era5[c].values, df_om[c].values, out[c].values)
            f_era5 = np.mean(era5_v <= UMBRAL_HUMEDO)
            f_raw  = np.mean(om_v   <= UMBRAL_HUMEDO)
            f_cor  = np.mean(cor_v  <= UMBRAL_HUMEDO)
            # KS de intensidad solo sobre húmedos de cada muestra
            def _ks_humedo(a, b):
                aw, bw = a[a > UMBRAL_HUMEDO], b[b > UMBRAL_HUMEDO]
                if len(aw) < 20 or len(bw) < 20:
                    return np.nan
                return ks_2samp(aw, bw).statistic
            diag[c] = {
                "tipo": "intermitente",
                "err_frac_seca_raw": abs(f_raw - f_era5),
                "err_frac_seca_cor": abs(f_cor - f_era5),
                "ks_intensidad_raw": _ks_humedo(om_v,  era5_v),
                "ks_intensidad_cor": _ks_humedo(cor_v, era5_v),
            }
        else:
            ks_raw = ks_2samp(df_om[c].values, df_era5[c].values).statistic
            ks_cor = ks_2samp(out[c].values,   df_era5[c].values).statistic
            diag[c] = {"tipo": "continua", "ks_raw": ks_raw, "ks_cor": ks_cor}
    return out, diag


# ----------------------------------------------------------------------
# CARGA DE DATOS REALES  (rellenar rutas)
# ----------------------------------------------------------------------
def cargar_era5(largo_unificado, planta):
    """ERA5 desde el largo_unificado del notebook, una planta."""
    g = (largo_unificado[largo_unificado.item_id == planta]
         .set_index("timestamp")
         .rename(columns={"potencia_mw": "_p"}))   # target no se usa aquí
    g["hour"] = g.index.hour
    return g[COVARS + ["hour"]]

def cargar_openmeteo(path_planta):
    """
    Open-Meteo Historical Forecast API, una planta, ya descargado a CSV/parquet.
    Debe traer columnas renombradas a COVARS. Ojo unidades:
      wind_speed: Open-Meteo da km/h -> /3.6 para m/s si ERA5 está en m/s
      pressure:   hPa
      ghi:        shortwave_radiation (W/m2)
    """
    df = pd.read_parquet(path_planta) if str(path_planta).endswith("parquet") \
         else pd.read_csv(path_planta, parse_dates=["timestamp"])
    df = df.set_index("timestamp")
    # EJEMPLO de renombrado/conversión — ajustar a tus columnas reales:
    ren = {"shortwave_radiation": "ghi", "temperature_2m": "t_air",
           "relative_humidity_2m": "hr", "wind_speed_10m": "wind_speed",
           "surface_pressure": "pressure"}
    df = df.rename(columns=ren)
    if df["wind_speed"].mean() > 20:      # heurística km/h -> m/s
        df["wind_speed"] = df["wind_speed"] / 3.6
    df["hour"] = df.index.hour
    return df[COVARS + ["hour"]]


# ----------------------------------------------------------------------
# DEMO sintética (verifica que corre; sustituir por el loop de 11 plantas)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    rng = np.random.default_rng(0)
    n = 8760
    idx = pd.date_range("2023-01-01", periods=n, freq="h")
    hour = idx.hour
    # ERA5 sintético con estructura diurna en GHI y colinealidad
    z = rng.standard_normal((n, 5))
    solar = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, 1)
    era5 = pd.DataFrame(index=idx)
    era5["ghi"]        = np.clip(solar * 800 + z[:, 0] * 60, 0, None)
    era5["t_air"]      = 18 + solar * 8 + z[:, 1] * 2
    era5["hr"]         = np.clip(70 - solar * 25 + z[:, 2] * 5, 0, 100)
    era5["wind_speed"] = np.clip(3 + solar * 2 + z[:, 3], 0, None)
    era5["pressure"]   = 1013 + z[:, 4] * 3
    # precip intermitente: ~85% horas secas en ERA5
    precip_era5 = rng.exponential(2.0, n) * (rng.random(n) < 0.15)
    era5["precip_mm"] = precip_era5
    era5["hour"] = hour
    # Open-Meteo: mismo patrón + sesgo sistemático
    om = era5.copy()
    om["ghi"]        = np.clip(era5["ghi"] * 1.08 + 15, 0, None)   # sesgo alto en GHI
    om["t_air"]      = era5["t_air"] + 0.6
    om["wind_speed"] = era5["wind_speed"] * 3.6 * 1.1              # en km/h + sesgo
    om["pressure"]   = era5["pressure"] - 1.5
    # OM predice lluvia MÁS seguido (menos horas secas) + intensidad sesgada
    precip_om = rng.exponential(2.6, n) * (rng.random(n) < 0.28)
    om["precip_mm"] = precip_om

    om_corr, diag = corregir_planta(era5, om)

    print("=== Variables continuas: KS antes/después ===")
    print(f"{'Var':<12}{'KS crudo':>12}{'KS corregido':>16}")
    print("-" * 40)
    for c in COVARS:
        d = diag[c]
        if d["tipo"] == "continua":
            print(f"{c:<12}{d['ks_raw']:>12.4f}{d['ks_cor']:>16.4f}")

    print("\n=== Precipitación (variable intermitente, evaluación en 2 componentes) ===")
    d = diag["precip_mm"]
    print(f"  Error frecuencia seca:  crudo {d['err_frac_seca_raw']:.4f}  ->  corregido {d['err_frac_seca_cor']:.4f}")
    print(f"  KS intensidad (húmedos): crudo {d['ks_intensidad_raw']:.4f}  ->  corregido {d['ks_intensidad_cor']:.4f}")

    print("\n=== Preservación de dependencia (correlación cruzada GHI-t_air) ===")
    print(f"  ERA5:         {era5[['ghi','t_air']].corr().iloc[0,1]:.3f}")
    print(f"  OM corregido: {om_corr[['ghi','t_air']].corr().iloc[0,1]:.3f}")
