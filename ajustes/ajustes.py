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
    st.info("💡 La configuración se conserva activa en tu sesión de trabajo.")