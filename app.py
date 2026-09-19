import os
import time
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import importlib
import db_manager
import auth
import data_manager
from reporte_ganancia_ciclo import reporte_ganancia_ciclo as modulo_reporte
from historico_semanal import historico_semanal as modulo_historico
from historial_general import historial_general as modulo_historial_general
from operacion_externa import operacion_externa as modulo_operacion
from ajustes import ajustes as modulo_ajustes

# Forzar recarga de módulos en caliente para evitar caché de Python
importlib.reload(db_manager)
importlib.reload(auth)
importlib.reload(data_manager)
importlib.reload(modulo_reporte)
importlib.reload(modulo_historico)
importlib.reload(modulo_historial_general)
importlib.reload(modulo_operacion)
importlib.reload(modulo_ajustes)

# Inicializar base de datos PostgreSQL persistente si aplica
try:
    db_manager.init_db()
except Exception:
    pass

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

                // 3. Ocultar de forma segura fuera de pantalla los botones técnicos de filtro (Filtro_Lunes, etc.) sin anular eventos
                const filterContainers = pDoc.querySelectorAll('div[class*="st-key-btn_flt_day_"], div[class*="st-key-btn_flt_op_day_"]');
                filterContainers.forEach(el => {
                    el.style.setProperty('position', 'fixed', 'important');
                    el.style.setProperty('top', '-9999px', 'important');
                    el.style.setProperty('left', '-9999px', 'important');
                    el.style.setProperty('width', '1px', 'important');
                    el.style.setProperty('height', '1px', 'important');
                    el.style.setProperty('min-height', '0px', 'important');
                    el.style.setProperty('opacity', '0', 'important');
                    el.style.setProperty('overflow', 'hidden', 'important');
                    el.style.setProperty('margin', '0px', 'important');
                    el.style.setProperty('padding', '0px', 'important');
                    el.style.setProperty('border', 'none', 'important');
                    el.style.setProperty('z-index', '-9999', 'important');
                });
                const allBtns = pDoc.querySelectorAll('button');
                allBtns.forEach(btn => {
                    const txt = (btn.textContent || btn.innerText || '').trim();
                    if (txt.startsWith('Filtro_') || txt.includes('Filtro_')) {
                        const elContainer = btn.closest('div[data-testid="stElementContainer"]') || btn.parentElement;
                        if (elContainer) {
                            elContainer.style.setProperty('position', 'fixed', 'important');
                            elContainer.style.setProperty('top', '-9999px', 'important');
                            elContainer.style.setProperty('left', '-9999px', 'important');
                            elContainer.style.setProperty('width', '1px', 'important');
                            elContainer.style.setProperty('height', '1px', 'important');
                            elContainer.style.setProperty('min-height', '0px', 'important');
                            elContainer.style.setProperty('opacity', '0', 'important');
                            elContainer.style.setProperty('overflow', 'hidden', 'important');
                            elContainer.style.setProperty('margin', '0px', 'important');
                            elContainer.style.setProperty('padding', '0px', 'important');
                            elContainer.style.setProperty('border', 'none', 'important');
                            elContainer.style.setProperty('z-index', '-9999', 'important');
                        }
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
                    const slug = card.getAttribute('data-dia-slug') || (dia ? dia.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '') : '');
                    if (slug || dia) {
                        const now = Date.now();
                        if (card._lastDayClick && (now - card._lastDayClick < 400)) return;
                        card._lastDayClick = now;
                        const targetBtn = pDoc.querySelector(`.st-key-btn_flt_day_${slug} button`) ||
                                          pDoc.querySelector(`.st-key-btn_flt_day_${dia} button`) ||
                                          Array.from(pDoc.querySelectorAll('button')).find(b => (b.textContent || '').includes(`Filtro_${dia}`));
                        if (targetBtn) {
                            targetBtn.click();
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
    v_param = st.query_params.get("view")
    if v_param in ["Reporte Ganancia Por Ciclo", "Histórico Semanal", "Historial General", "Registrar Operación Externa", "Ajustes"]:
        st.session_state["vista_actual"] = v_param
    else:
        st.session_state["vista_actual"] = "Reporte Ganancia Por Ciclo"

usuario_activo = st.session_state.get("usuario_activo", {"username": "Victoria", "nombre": "Victoria", "role": "operador"})
es_admin = usuario_activo.get("role") == "admin"

OPCIONES_MENU = {
    "Reporte Ganancia Por Ciclo": "⚡",
    "Histórico Semanal": "📊",
    "Historial General": "📜",
    "Registrar Operación Externa": "➕",
}
if es_admin:
    OPCIONES_MENU["Ajustes"] = "⚙️"

# Si el usuario no es admin y está en Ajustes, redirigir a Reporte
if not es_admin and st.session_state.get("vista_actual") == "Ajustes":
    st.session_state["vista_actual"] = "Reporte Ganancia Por Ciclo"
    st.query_params["view"] = "Reporte Ganancia Por Ciclo"

# SIDEBAR DE NAVEGACIÓN
with st.sidebar:
    st.markdown("### 🦆 RicoMcPato")
    badge_icon = "👑" if es_admin else "👤"
    badge_role = "Admin" if es_admin else "Operador"
    color_role = "#f59e0b" if es_admin else "#58a6ff"
    st.markdown(f"""
    <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 6px 10px; margin-bottom: 12px; font-size: 0.84rem; display: flex; align-items: center; justify-content: space-between;">
        <span style="color: #f0f6fc; font-weight: 600;">{badge_icon} {usuario_activo.get('nombre', 'Usuario')}</span>
        <span style="background: #21262d; border: 1px solid #30363d; color: {color_role}; font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 4px;">{badge_role}</span>
    </div>
    """, unsafe_allow_html=True)

    for nombre, icono in OPCIONES_MENU.items():
        tipo_btn = "primary" if st.session_state["vista_actual"] == nombre else "secondary"
        if st.button(f"{nombre}  {icono}", key=f"nav_{nombre}", type=tipo_btn, use_container_width=True, help=nombre):
            if st.session_state.get("vista_actual") != nombre:
                st.session_state["vista_actual"] = nombre
                st.query_params["view"] = nombre
                if nombre == "Histórico Semanal":
                    st.session_state["filtro_dia_semana"] = None
                elif nombre == "Registrar Operación Externa":
                    st.session_state["filtro_dia_op_ext"] = None
            st.rerun()

    st.write("")
    if st.button("Cerrar Sesión 🚪", key="btn_lock_session", type="secondary", use_container_width=True, help="Cerrar sesión segura"):
        auth.cerrar_sesion()

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

elif vista == "Historial General":
    cargar_css("historial_general/historial_general.css")
    modulo_historial_general.render_vista()

elif vista == "Registrar Operación Externa":
    cargar_css("operacion_externa/operacion_externa.css")
    modulo_operacion.render_vista()

elif vista == "Ajustes":
    cargar_css("ajustes/ajustes.css")
    modulo_ajustes.render_vista()