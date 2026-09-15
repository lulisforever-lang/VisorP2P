import os
from datetime import datetime
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

COLUMNS_HISTORICO = ["Fecha_Hora", "Ciclo", "Comision_Pct", "Tasa_Venta", "Tasa_Compra", "Capital", "Ganancia_Pct", "USDT_Ganado", "Ajuste"]
COLUMNS_MANUAL = ["id", "Fecha_Hora", "tradeType", "amount", "unitPrice", "totalPrice", "commission", "fiat", "nota", "orderStatus"]

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

def guardar_ciclo(nuevo_registro: dict) -> bool:
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

def reiniciar_semana() -> bool:
    df_vacio = pd.DataFrame(columns=COLUMNS_HISTORICO)
    
    # 1. Limpiar local
    df_vacio.to_csv(DB_HISTORICO_FILE, index=False)

    # 2. Limpiar Google Sheets
    conn = _get_gsheets_connection()
    if conn is not None:
        try:
            conn.update(worksheet="historico_ciclos", data=df_vacio)
        except Exception as e:
            st.error(f"Error reiniciando semana en Google Sheets: {e}")
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

    return pd.read_csv(DB_MANUAL_FILE)

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
