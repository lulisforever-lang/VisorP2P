import os
import time
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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

def desactivar_teclado_virtual():
    """
    Evita que se despliegue el teclado virtual táctil en dispositivos móviles
    al pulsar selectores (st.selectbox como Hora, Minuto, Periodo) o selectores
    de fecha (st.date_input), preservando la interacción táctil directa con los desplegables.
    """
    components.html("""
    <script>
    (function() {
        const pDoc = window.parent.document;
        if (!pDoc) return;

        function applyMobileFixes() {
            try {
                // 1. Desactivar teclado en selectboxes manteniendo el desplegable interactivo
                const selectInputs = pDoc.querySelectorAll('div[data-testid="stSelectbox"] input');
                selectInputs.forEach(inp => {
                    if (inp.getAttribute('inputmode') !== 'none') {
                        inp.setAttribute('inputmode', 'none');
                    }
                    if (!inp.readOnly) {
                        inp.readOnly = true;
                    }
                });

                // 2. Desactivar teclado en los números de fecha (DateField spinbuttons)
                const dateSpans = pDoc.querySelectorAll('div[data-testid="stDateInput"] span[role="spinbutton"]');
                dateSpans.forEach(span => {
                    if (span.getAttribute('inputmode') !== 'none') {
                        span.setAttribute('inputmode', 'none');
                    }
                    if (span.getAttribute('contenteditable') !== 'false') {
                        span.setAttribute('contenteditable', 'false');
                    }
                });
            } catch(e) {}
        }

        // Listener para abrir el selector nativo de fecha al tocar el campo de fecha
        if (!pDoc._stMobileDatePickerAttached) {
            pDoc._stMobileDatePickerAttached = true;

            pDoc.addEventListener('click', function(e) {
                const dateContainer = e.target.closest('div[data-testid="stDateInput"]');
                if (dateContainer) {
                    const hiddenDate = dateContainer.querySelector('input[type="date"]');
                    if (hiddenDate && typeof hiddenDate.showPicker === 'function') {
                        try {
                            hiddenDate.showPicker();
                        } catch(err) {}
                    }
                }
            }, true);

            // Sincronizar cambios de fecha desde el selector nativo hacia React/Streamlit
            pDoc.addEventListener('change', function(e) {
                if (e.target && e.target.type === 'date') {
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
                    if (setter) {
                        setter.call(e.target, e.target.value);
                    }
                    e.target.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }, true);

            // Suprimir teclado de forma preventiva ante eventos de foco y pulsación
            pDoc.addEventListener('focusin', function(e) {
                const t = e.target;
                if (!t) return;
                if (t.closest('div[data-testid="stSelectbox"]')) {
                    t.setAttribute('inputmode', 'none');
                    if (t.tagName === 'INPUT') t.readOnly = true;
                } else if (t.closest('div[data-testid="stDateInput"]')) {
                    t.setAttribute('inputmode', 'none');
                    if (t.tagName === 'SPAN') t.setAttribute('contenteditable', 'false');
                }
            }, true);

            pDoc.addEventListener('pointerdown', function(e) {
                const t = e.target;
                if (!t) return;
                if (t.closest('div[data-testid="stSelectbox"]') || t.closest('div[data-testid="stDateInput"]')) {
                    applyMobileFixes();
                }
            }, true);

            // Listener para interactuar con las tarjetas de días como botones en Histórico Semanal
            pDoc.addEventListener('click', function(e) {
                const card = e.target.closest('.metric-day-card');
                if (card) {
                    const dia = card.getAttribute('data-dia');
                    if (dia) {
                        const btn = Array.from(pDoc.querySelectorAll('button')).find(b => b.innerText.trim() === `Filtro_${dia}`);
                        if (btn) {
                            btn.click();
                        }
                    }
                }
            }, true);

            // Observar mutaciones dinámicas del DOM para aplicar en tiempo real
            const observer = new MutationObserver(function() {
                applyMobileFixes();
            });
            observer.observe(pDoc.body, { childList: true, subtree: true });
        }

        applyMobileFixes();
    })();
    </script>
    """, height=0)

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

# Desactivar teclado virtual táctil en selectores y fechas para dispositivos móviles
desactivar_teclado_virtual()

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