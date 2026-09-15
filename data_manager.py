import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

DEFAULT_TIMEZONE = "America/Caracas"

def get_app_timezone():
    tz_str = DEFAULT_TIMEZONE
    try:
        if hasattr(st, "session_state") and "cfg_timezone" in st.session_state and st.session_state["cfg_timezone"]:
            tz_str = st.session_state["cfg_timezone"]
        elif hasattr(st, "secrets") and "APP_TIMEZONE" in st.secrets:
            tz_str = st.secrets["APP_TIMEZONE"]
        elif os.getenv("APP_TIMEZONE"):
            tz_str = os.getenv("APP_TIMEZONE")
    except Exception:
        pass
    try:
        return ZoneInfo(tz_str)
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)

def get_now_local() -> datetime:
    return datetime.now(get_app_timezone())

DB_HISTORICO_FILE = "historico_ciclos.csv"
DB_MANUAL_FILE = "operaciones_manuales.csv"

COLUMNS_HISTORICO = ["Fecha_Hora", "Ciclo", "Comision_Pct", "Tasa_Venta", "Tasa_Compra", "Capital", "Ganancia_Pct", "USDT_Ganado", "Ajuste", "Usuario"]
COLUMNS_MANUAL = ["id", "Fecha_Hora", "tradeType", "amount", "unitPrice", "totalPrice", "commission", "fiat", "nota", "orderStatus", "Usuario"]

def _tiene_gsheets_configurado():
    try:
        if hasattr(st, "secrets") and "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            return True
    except Exception:
        pass
    return False

def _get_gsheets_connection():
    if not _tiene_gsheets_configurado():
        return None
    try:
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception:
        return None

# ======================================================================
# HISTORICO DE CICLOS
# ======================================================================

def get_historico() -> pd.DataFrame:
    conn = _get_gsheets_connection()
    if conn is not None:
        try:
            df = conn.read(worksheet="historico_ciclos", ttl=0)
            if df is not None and not df.empty:
                df = df.dropna(how="all")
                for col in COLUMNS_HISTORICO:
                    if col not in df.columns:
                        df[col] = None
                return df
        except Exception:
            pass

    # Fallback local
    if not os.path.exists(DB_HISTORICO_FILE):
        df_init = pd.DataFrame(columns=COLUMNS_HISTORICO)
        df_init.to_csv(DB_HISTORICO_FILE, index=False)
        return df_init

    df = pd.read_csv(DB_HISTORICO_FILE)
    return df

def enriquecer_historico_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriquece el DataFrame histórico con conversiones numéricas y temporales
    (Día, Semana Lun-Dom, Mes, Año) para filtrado flexible.
    """
    if df is None or df.empty or "Fecha_Hora" not in df.columns:
        return pd.DataFrame(columns=COLUMNS_HISTORICO)

    df = df.copy()
    for col in ["Capital", "Ganancia_Pct", "Ajuste", "USDT_Ganado", "Tasa_Venta", "Tasa_Compra", "Comision_Pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    if "Ciclo" in df.columns:
        df["Ciclo"] = pd.to_numeric(df["Ciclo"], errors="coerce").fillna(0).astype(int)

    df["DT_Parsed"] = pd.to_datetime(df["Fecha_Hora"], dayfirst=True, errors="coerce")
    df["Fecha_Date"] = df["DT_Parsed"].dt.date

    nombres_dias = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    df["Dia_Semana"] = df["DT_Parsed"].dt.dayofweek.map(nombres_dias)

    # Inicio (Lunes) y Fin (Domingo) de la semana de cada ciclo
    df["Lunes_Semana"] = df["DT_Parsed"].apply(
        lambda dt: (dt.date() - timedelta(days=dt.weekday())) if pd.notnull(dt) else None
    )
    df["Domingo_Semana"] = df["Lunes_Semana"].apply(
        lambda lun: (lun + timedelta(days=6)) if lun else None
    )
    df["Semana_Key"] = df["Lunes_Semana"].apply(
        lambda lun: lun.strftime("%Y-%m-%d") if lun else "sin-fecha"
    )
    df["Semana_Label"] = df.apply(
        lambda r: f"Semana del {r['Lunes_Semana'].strftime('%d/%m/%Y')} al {r['Domingo_Semana'].strftime('%d/%m/%Y')}" if r['Lunes_Semana'] else "Sin Fecha",
        axis=1
    )
    df["Mes_Key"] = df["DT_Parsed"].apply(lambda dt: dt.strftime("%Y-%m") if pd.notnull(dt) else "sin-mes")
    nombres_meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    df["Mes_Label"] = df["DT_Parsed"].apply(
        lambda dt: f"{nombres_meses.get(dt.month, '')} {dt.year}" if pd.notnull(dt) else "Sin Mes"
    )
    if "Usuario" not in df.columns:
        df["Usuario"] = "Victoria"
    else:
        df["Usuario"] = df["Usuario"].fillna("Victoria").replace("", "Victoria")

    df["Anio"] = df["DT_Parsed"].apply(lambda dt: int(dt.year) if pd.notnull(dt) else 0)
    return df

def get_rango_semana_actual() -> tuple:
    """Devuelve (lunes_date, domingo_date, etiqueta_str) para la semana de hoy."""
    now = get_now_local().date()
    lunes = now - timedelta(days=now.weekday())
    domingo = lunes + timedelta(days=6)
    label = f"Semana del {lunes.strftime('%d/%m/%Y')} al {domingo.strftime('%d/%m/%Y')}"
    return lunes, domingo, label

def guardar_ciclo(nuevo_registro: dict) -> bool:
    if "Usuario" not in nuevo_registro or not nuevo_registro["Usuario"]:
        usr = "Victoria"
        if hasattr(st, "session_state") and "usuario_activo" in st.session_state and st.session_state["usuario_activo"]:
            usr = st.session_state["usuario_activo"].get("username", "Victoria")
        nuevo_registro["Usuario"] = usr

    df_actual = get_historico()
    nuevo_df = pd.DataFrame([nuevo_registro])
    df_actualizado = pd.concat([df_actual, nuevo_df], ignore_index=True)

    # 1. Guardar copia local
    try:
        df_actualizado.to_csv(DB_HISTORICO_FILE, index=False)
    except Exception:
        pass

    # 2. Guardar en Google Sheets
    conn = _get_gsheets_connection()
    if conn is not None:
        try:
            conn.update(worksheet="historico_ciclos", data=df_actualizado)
            return True
        except Exception as e:
            st.error(f"Error sincronizando ciclo con Google Sheets: {e}")
            return False

    return True

def actualizar_ajuste_ciclo(ciclo_num: int, nuevo_ajuste: float) -> bool:
    df = get_historico()
    if df.empty:
        return False

    df["Ciclo_Num"] = pd.to_numeric(df["Ciclo"], errors="coerce")
    mask = df["Ciclo_Num"] == int(ciclo_num)
    if not mask.any():
        return False

    idx = df[mask].index[0]

    old_ajuste = float(pd.to_numeric(df.loc[idx, "Ajuste"], errors="coerce")) if pd.notnull(df.loc[idx, "Ajuste"]) else 0.0
    old_usdt_ganado = float(pd.to_numeric(df.loc[idx, "USDT_Ganado"], errors="coerce")) if pd.notnull(df.loc[idx, "USDT_Ganado"]) else 0.0
    capital = float(pd.to_numeric(df.loc[idx, "Capital"], errors="coerce")) if pd.notnull(df.loc[idx, "Capital"]) else 0.0

    # Profit base del ciclo antes de ajustes
    profit_base = old_usdt_ganado - old_ajuste
    nuevo_usdt_ganado = round(profit_base + nuevo_ajuste, 2)
    nuevo_pct = round((nuevo_usdt_ganado / capital * 100) if capital > 0 else 0.0, 2)

    df.loc[idx, "Ajuste"] = round(nuevo_ajuste, 2)
    df.loc[idx, "USDT_Ganado"] = nuevo_usdt_ganado
    df.loc[idx, "Ganancia_Pct"] = nuevo_pct

    df = df.drop(columns=["Ciclo_Num"])

    # 1. Guardar copia local
    try:
        df.to_csv(DB_HISTORICO_FILE, index=False)
    except Exception:
        pass

    # 2. Guardar en Google Sheets si aplica
    conn = _get_gsheets_connection()
    if conn is not None:
        try:
            conn.update(worksheet="historico_ciclos", data=df)
            return True
        except Exception as e:
            st.error(f"Error actualizando ciclo en Google Sheets: {e}")
            return False

    return True

# =======================================================================
# OPERACIONES MANUALES / EXTERNAS (OTC)
# ======================================================================

def get_todas_operaciones_manuales() -> pd.DataFrame:
    conn = _get_gsheets_connection()
    if conn is not None:
        try:
            df = conn.read(worksheet="operaciones_manuales", ttl=0)
            if df is not None and not df.empty:
                df = df.dropna(how="all")
                for col in COLUMNS_MANUAL:
                    if col not in df.columns:
                        df[col] = None
                return df
        except Exception:
            pass

    if not os.path.exists(DB_MANUAL_FILE):
        df_init = pd.DataFrame(columns=COLUMNS_MANUAL)
        df_init.to_csv(DB_MANUAL_FILE, index=False)
        return df_init

    df = pd.read_csv(DB_MANUAL_FILE)
    if "Usuario" not in df.columns:
        df["Usuario"] = "Victoria"
    else:
        df["Usuario"] = df["Usuario"].fillna("Victoria")
    return df

def get_operaciones_manuales_filtradas(t_type: str, start_dt, end_dt) -> pd.DataFrame:
    df = get_todas_operaciones_manuales()
    if df.empty:
        return pd.DataFrame()

    df["Fecha_Hora"] = pd.to_datetime(df["Fecha_Hora"], errors="coerce")
    df = df[(df["tradeType"] == t_type) & (df["Fecha_Hora"] >= start_dt) & (df["Fecha_Hora"] <= end_dt)]
    if df.empty:
        return pd.DataFrame()

    df["Origen"] = "Externo (Directo)"
    df["totalPrice_nominal"] = df["totalPrice"]
    cols = ["Fecha_Hora", "tradeType", "amount", "unitPrice", "totalPrice", "totalPrice_nominal", "commission", "orderStatus", "Origen", "nota"]
    return df[cols]

def guardar_operacion_manual(nuevo_registro: dict) -> bool:
    if "Usuario" not in nuevo_registro or not nuevo_registro["Usuario"]:
        usr = "Victoria"
        if hasattr(st, "session_state") and "usuario_activo" in st.session_state and st.session_state["usuario_activo"]:
            usr = st.session_state["usuario_activo"].get("username", "Victoria")
        nuevo_registro["Usuario"] = usr

    df_actual = get_todas_operaciones_manuales()
    nuevo_df = pd.DataFrame([nuevo_registro])
    df_actualizado = pd.concat([df_actual, nuevo_df], ignore_index=True)

    # 1. Guardar copia local
    try:
        df_actualizado.to_csv(DB_MANUAL_FILE, index=False)
    except Exception:
        pass

    # 2. Guardar en Google Sheets
    conn = _get_gsheets_connection()
    if conn is not None:
        try:
            conn.update(worksheet="operaciones_manuales", data=df_actualizado)
            return True
        except Exception as e:
            st.error(f"Error sincronizando operación con Google Sheets: {e}")
            return False

    return True

def actualizar_operacion_manual(op_id: str, datos_actualizados: dict) -> bool:
    df = get_todas_operaciones_manuales()
    if df.empty:
        return False

    mask = df["id"].astype(str) == str(op_id)
    if not mask.any():
        return False

    for col, val in datos_actualizados.items():
        if col in df.columns:
            df.loc[mask, col] = val

    # 1. Guardar copia local
    try:
        df.to_csv(DB_MANUAL_FILE, index=False)
    except Exception:
        pass

    # 2. Guardar en Google Sheets
    conn = _get_gsheets_connection()
    if conn is not None:
        try:
            conn.update(worksheet="operaciones_manuales", data=df)
            return True
        except Exception as e:
            st.error(f"Error actualizando operación en Google Sheets: {e}")
            return False

    return True

def eliminar_operacion_manual(op_id: str) -> bool:
    df = get_todas_operaciones_manuales()
    if df.empty:
        return False

    mask = df["id"].astype(str) == str(op_id)
    if not mask.any():
        return False

    df = df[~mask]

    # 1. Guardar copia local
    try:
        df.to_csv(DB_MANUAL_FILE, index=False)
    except Exception:
        pass

    # 2. Guardar en Google Sheets
    conn = _get_gsheets_connection()
    if conn is not None:
        try:
            conn.update(worksheet="operaciones_manuales", data=df)
            return True
        except Exception as e:
            st.error(f"Error eliminando operación en Google Sheets: {e}")
            return False

    return True
