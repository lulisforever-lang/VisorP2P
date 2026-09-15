import os
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent

def cargar_css(ruta_relativa):
    ruta = BASE_DIR / ruta_relativa
    if ruta.exists():
        with open(ruta, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def get_configured_pin():
    try:
        if hasattr(st, 'secrets') and 'APP_PIN' in st.secrets:
            return str(st.secrets['APP_PIN']).strip()
    except Exception:
        pass

    env_pin = os.getenv('APP_PIN', '').strip()
    if env_pin:
        return env_pin

    return '1234'

def verificar_acceso():
    if st.session_state.get('autenticado', False):
        return True

    cargar_css('auth.css')
    pin_correcto = get_configured_pin()

    with st.form('form_login', clear_on_submit=False):
        st.markdown('''
            <div class="login-header-box">
                <div class="login-brand-title">
                    <span>🦆</span>
                    <span>RicoMcPato</span>
                </div>
                <div class="login-pill-badge">Visor Financiero P2P</div>
                <div class="login-lock-heading">
                    <span>🔒</span> Acceso Protegido
                </div>
                <p class="login-subtext">Introduce tu PIN de seguridad para acceder al visor financiero.</p>
            </div>
        ''', unsafe_allow_html=True)

        st.markdown('<label class="login-input-label">PIN de Acceso:</label>', unsafe_allow_html=True)
        pin_ingresado = st.text_input(
            'PIN de Acceso:',
            type='password',
            placeholder='Ingresa tu PIN',
            max_chars=20,
            label_visibility='collapsed'
        )
        btn_entrar = st.form_submit_button('Desbloquear 🔓', type='primary', use_container_width=True)

        if btn_entrar:
            if pin_ingresado and pin_ingresado.strip() == pin_correcto:
                st.session_state['autenticado'] = True
                st.success('Acceso concedido.')
                st.rerun()
            else:
                st.error('❌ PIN incorrecto. Inténtalo de nuevo.')

        st.markdown('''
            <div class="login-footer-pill">
                <span>🛡️</span>
                <span>Acceso local seguro &bull; Operador autorizado</span>
            </div>
        ''', unsafe_allow_html=True)

    st.stop()
