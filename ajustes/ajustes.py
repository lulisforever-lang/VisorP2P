import streamlit as st

def render_vista():
    st.title("⚙️ Ajustes del Sistema y Pagos Bancarios")
    st.caption("Configura las políticas operativas y fórmulas aplicadas a tus ciclos.")

    st.write("#### 🏦 Parámetros de Conciliación Bancaria")
    c_chk1 = st.checkbox(
        "Redondear compras al entero superior",
        value=st.session_state["cfg_redondear_pagos"],
        help="Ajusta cada pago al entero superior en bolívares (ej. 287.642,10 -> 287.643 VES)."
    )
    st.session_state["cfg_redondear_pagos"] = c_chk1

    c_chk2 = st.checkbox(
        "Descontar costo de redondeo de la ganancia neta",
        value=st.session_state["cfg_descontar_redondeo"],
        help="Convierte los bolívares de más transferidos a USDT y los resta del profit líquido."
    )
    st.session_state["cfg_descontar_redondeo"] = c_chk2

    c_chk3 = st.checkbox(
        "Incluir órdenes pagadas en espera de liberación (PAID)",
        value=st.session_state["cfg_incluir_pagadas"],
        help="Suma las órdenes ya transferidas en el banco que esperan que la contraparte libere."
    )
    st.session_state["cfg_incluir_pagadas"] = c_chk3

    st.divider()
    st.write("#### 🌍 Zona Horaria Operativa")
    st.caption("Sincroniza tus órdenes con tu reloj local, resolviendo diferencias si el servidor en la nube está en Alemania u otro país.")

    ZONAS = {
        "America/Caracas": "🇻🇪 Venezuela (UTC-4 - Caracas)",
        "America/Bogota": "🇨🇴 Colombia (UTC-5 - Bogotá)",
        "America/Lima": "🇵🇪 Perú (UTC-5 - Lima)",
        "America/Buenos_Aires": "🇦🇷 Argentina (UTC-3 - Buenos Aires)",
        "America/Santiago": "🇨🇱 Chile (UTC-3/UTC-4 - Santiago)",
        "America/Mexico_City": "🇲🇽 México (UTC-6 - CDMX)",
        "America/New_York": "🇺🇸 EE.UU. Este (UTC-4/UTC-5 - New York)",
        "Europe/Madrid": "🇪🇸 España (UTC+1/UTC+2 - Madrid)",
        "UTC": "🌐 Tiempo Universal Coordinado (UTC)"
    }

    current_tz = st.session_state.get("cfg_timezone", "America/Caracas")
    opciones = list(ZONAS.keys())
    idx = opciones.index(current_tz) if current_tz in opciones else 0

    nueva_tz = st.selectbox(
        "Zona Horaria para Reportes:",
        opciones,
        index=idx,
        format_func=lambda x: ZONAS.get(x, x),
        help="Las órdenes de Binance y registros manuales se alinean exactamente a esta zona horaria."
    )
    if nueva_tz != current_tz:
        st.session_state["cfg_timezone"] = nueva_tz
        st.rerun()

    st.divider()
    st.info("💡 La configuración se conserva activa en tu sesión de trabajo.")