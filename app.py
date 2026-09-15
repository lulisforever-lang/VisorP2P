import os
import time
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import streamlit as st

import importlib
import auth
import data_manager
from reporte_ganancia_ciclo import reporte_ganancia_ciclo as modulo_reporte
from historico_semanal import historico_semanal as modulo_historico
from operacion_externa import operacion_externa as modulo_operacion
from ajustes import ajustes as modulo_ajustes

# Forzar recarga de módulos en caliente para evitar caché de Python
importlib.reload(auth)
importlib.reload(data_manager)
importlib.reload(modulo_reporte)
importlib.reload(modulo_historico)
importlib.reload(modulo_operacion)
importlib.reload(modulo_ajustes)

# Localizar la ruta exacta del archivo .env en la misma carpeta de app.py
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Cargar variables de entorno (override=True fuerza a recargar si editaste el archivo)
load_dotenv(dotenv_path=ENV_PATH, override=True)

# Configurar zona horaria del sistema en servidores Linux (ej. Render)
try:
    tz_env = os.getenv("APP_TIMEZONE", "America/Caracas")
    if hasattr(time, "tzset"):
        os.environ["TZ"] = tz_env
        time.tzset()
except Exception:
    pass

def get_binance_credentials():
    k = ""
    s = ""
    try:
        if hasattr(st, "secrets"):
            k = st.secrets.get("BINANCE_API_KEY") or st.secrets.get("binance_api_key") or ""
            s = st.secrets.get("BINANCE_API_SECRET") or st.secrets.get("binance_api_secret") or ""
    except Exception:
        pass
    if not k:
        k = os.getenv("BINANCE_API_KEY", "") or os.getenv("binance_api_key", "")
    if not s:
        s = os.getenv("BINANCE_API_SECRET", "") or os.getenv("binance_api_secret", "")
    return str(k).strip().strip('"').strip("'"), str(s).strip().strip('"').strip("'")

API_KEY, API_SECRET = get_binance_credentials()

st.set_page_config(page_title="RicoMcPato", layout="wide")

# Función para inyectar CSS externo
def cargar_css(ruta_relativa):
    ruta = BASE_DIR / ruta_relativa
    if ruta.exists():
        with open(ruta, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Cargamos el CSS global y del sidebar
cargar_css("app.css")

# Verificación de seguridad (Pantalla de bloqueo PIN)
auth.verificar_acceso()

# Configuración de políticas de conciliación en sesión
if "cfg_redondear_pagos" not in st.session_state:
    st.session_state["cfg_redondear_pagos"] = True
if "cfg_descontar_redondeo" not in st.session_state:
    st.session_state["cfg_descontar_redondeo"] = True
if "cfg_incluir_pagadas" not in st.session_state:
    st.session_state["cfg_incluir_pagadas"] = True
if "cfg_timezone" not in st.session_state:
    st.session_state["cfg_timezone"] = os.getenv("APP_TIMEZONE", "America/Caracas")

# Estado de la vista activa
if "vista_actual" not in st.session_state:
    st.session_state["vista_actual"] = "Reporte Ganancia Por Ciclo"

OPCIONES_MENU = {
    "Reporte Ganancia Por Ciclo": "⚡",
    "Histórico Semanal": "📊",
    "Registrar Operación Externa": "➕",
    "Ajustes": "⚙️"
}

# SIDEBAR DE NAVEGACIÓN
with st.sidebar:
    st.markdown("### 🦆 RicoMcPato")
    st.write("")

    for nombre, icono in OPCIONES_MENU.items():
        tipo_btn = "primary" if st.session_state["vista_actual"] == nombre else "secondary"
        if st.button(f"{nombre}  {icono}", key=f"nav_{nombre}", type=tipo_btn, use_container_width=True, help=nombre):
            st.session_state["vista_actual"] = nombre
            st.rerun()

    st.write("")
    if st.button("Bloquear 🔒", key="btn_lock_session", type="secondary", use_container_width=True, help="Bloquear sesión"):
        st.session_state["autenticado"] = False
        st.rerun()

vista = st.session_state["vista_actual"]

# ENRUTADOR POR MÓDULO (Carga su CSS dedicado y ejecuta su vista)
if vista == "Reporte Ganancia Por Ciclo":
    cargar_css("reporte_ganancia_ciclo/reporte_ganancia_ciclo.css")
    modulo_reporte.render_vista(API_KEY, API_SECRET)

elif vista == "Histórico Semanal":
    cargar_css("historico_semanal/historico_semanal.css")
    modulo_historico.render_vista()

elif vista == "Registrar Operación Externa":
    cargar_css("operacion_externa/operacion_externa.css")
    modulo_operacion.render_vista()

elif vista == "Ajustes":
    cargar_css("ajustes/ajustes.css")
    modulo_ajustes.render_vista()