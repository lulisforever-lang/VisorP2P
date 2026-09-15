import streamlit as st
import auth

def render_vista():
    usuario_activo = st.session_state.get("usuario_activo", {})
    if usuario_activo.get("role") != "admin":
        st.error("⛔ Acceso restringido. Esta sección de configuración es exclusiva para el Administrador.")
        return

    st.title("⚙️ Ajustes del Sistema y Gestión de Operadores")
    st.caption(f"Panel de Control Administrativo &bull; Sesión activa: **{usuario_activo.get('nombre', 'Admin')}** (👑 Administrador)")

    # Pestañas para organizar la administración
    tab_operadores, tab_conciliacion, tab_zona = st.tabs([
        "👥 Gestión de Colaboradores",
        "🏦 Conciliación Bancaria",
        "🌍 Zona Horaria Operativa"
    ])

    # =========================================================================
    # TAB 1: GESTIÓN DE COLABORADORES
    # =========================================================================
    with tab_operadores:
        st.write("#### 📋 Colaboradores Registrados")
        usuarios = auth.listar_usuarios()

        col_u1, col_u2 = st.columns([1.6, 1.4])
        with col_u1:
            for u in usuarios:
                badge_role = "👑 Administrador" if u["role"] == "admin" else "👤 Operador"
                color_role = "#f59e0b" if u["role"] == "admin" else "#58a6ff"
                st.markdown(f"""
                <div style="background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 10px 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #f0f6fc; font-size: 1rem;">{u['nombre']}</strong>
                        <span style="color: #8b949e; font-size: 0.82rem; margin-left: 6px;">(@{u['username']})</span>
                    </div>
                    <span style="background: #21262d; border: 1px solid #30363d; color: {color_role}; font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 6px;">
                        {badge_role}
                    </span>
                </div>
                """, unsafe_allow_html=True)

        with col_u2:
            with st.expander("➕ Registrar Nuevo Colaborador", expanded=False):
                with st.form("form_nuevo_operador", clear_on_submit=True):
                    n_user = st.text_input("Nombre de Usuario (sin espacios):", placeholder="Ej: Pedro")
                    n_nombre = st.text_input("Nombre completo o alias:", placeholder="Ej: Pedro Gómez")
                    n_pass = st.text_input("Contraseña inicial:", type="password", placeholder="Mínimo 4 caracteres")
                    btn_crear = st.form_submit_button("Crear Colaborador 👤", type="primary", use_container_width=True)

                    if btn_crear:
                        if n_user and n_pass:
                            ok, msg = auth.crear_usuario(n_user.strip(), n_pass.strip(), n_nombre.strip(), role="operador")
                            if ok:
                                st.success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                        else:
                            st.warning("Completa el usuario y la contraseña.")

            with st.expander("🔑 Restablecer Contraseña de Colaborador", expanded=False):
                operadores_edit = [u["username"] for u in usuarios if u["role"] != "admin" or u["username"] == usuario_activo.get("username")]
                if operadores_edit:
                    with st.form("form_cambiar_pass", clear_on_submit=True):
                        usr_sel_pass = st.selectbox("Seleccionar Usuario:", operadores_edit)
                        new_pwd = st.text_input("Nueva Contraseña:", type="password", placeholder="Ingresa la nueva clave")
                        btn_chg_pass = st.form_submit_button("Actualizar Contraseña 💾", type="primary", use_container_width=True)

                        if btn_chg_pass:
                            if new_pwd:
                                ok, msg = auth.cambiar_password(usr_sel_pass, new_pwd.strip())
                                if ok:
                                    st.success(f"✅ {msg}")
                                else:
                                    st.error(f"❌ {msg}")
                            else:
                                st.warning("Escribe la nueva contraseña.")

            with st.expander("🗑️ Eliminar Colaborador", expanded=False):
                operadores_del = [u["username"] for u in usuarios if u["role"] != "admin"]
                if operadores_del:
                    with st.form("form_eliminar_usr", clear_on_submit=True):
                        usr_a_eliminar = st.selectbox("Seleccionar Colaborador a Retirar:", operadores_del)
                        btn_del = st.form_submit_button("Confirmar Eliminación ⚠️", type="secondary", use_container_width=True)
                        if btn_del:
                            ok, msg = auth.eliminar_usuario(usr_a_eliminar)
                            if ok:
                                st.success(f"✅ {msg}")
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                else:
                    st.caption("No hay colaboradores adicionales para eliminar.")

    # =========================================================================
    # TAB 2: CONCILIACIÓN BANCARIA
    # =========================================================================
    with tab_conciliacion:
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

    # =========================================================================
    # TAB 3: ZONA HORARIA
    # =========================================================================
    with tab_zona:
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
    st.info("💡 La configuración y los usuarios se sincronizan de forma inmediata.")