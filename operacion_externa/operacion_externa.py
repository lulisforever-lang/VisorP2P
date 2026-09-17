import math
import os
import time
from datetime import datetime
import pandas as pd
import streamlit as st
import data_manager

FIAT_CURRENCY = "VES"

HORAS_12 = [f"{i:02d}" for i in range(1, 13)]
MINUTOS = [f"{i:02d}" for i in range(0, 60)]
PERIODOS = ["AM", "PM"]

def convertir_a_datetime(fecha, hora_str, minuto_str, periodo):
    h = int(hora_str)
    m = int(minuto_str)
    if periodo == "PM" and h != 12:
        h += 12
    elif periodo == "AM" and h == 12:
        h = 0
    return datetime(fecha.year, fecha.month, fecha.day, h, m)

@st.dialog("✏️ Editar Operación Externa")
def editar_operacion_dialog(op: dict):
    op_id = str(op["id"])
    st.markdown(f"Modificar datos de la operación **#{op_id}**")

    # Parse Fecha_Hora
    dt_val = None
    try:
        dt_val = datetime.strptime(str(op.get("Fecha_Hora", "")), "%Y-%m-%d %H:%M:%S")
    except Exception:
        dt_val = data_manager.get_now_local()

    c1, c2, c3 = st.columns(3)
    with c1:
        tipo_actual = str(op.get("tradeType", "SELL")).upper()
        tipo_idx = 0 if "SELL" in tipo_actual else 1
        trade_type_ui = st.selectbox("Tipo de Operación:", ["Venta Externa (SELL)", "Compra Externa (BUY)"], index=tipo_idx, key=f"dlg_type_{op_id}")
        trade_code = "SELL" if "SELL" in trade_type_ui else "BUY"
    with c2:
        m_usdt = st.number_input("Monto en USDT:", min_value=0.0, value=float(op.get("amount", 0.0)), step=10.0, format="%.2f", key=f"dlg_usdt_{op_id}")
    with c3:
        m_tasa = st.number_input(f"Tasa de Cambio ({FIAT_CURRENCY}):", min_value=0.0, value=float(op.get("unitPrice", 0.0)), step=0.1, format="%.3f", key=f"dlg_tasa_{op_id}")

    c4, c5 = st.columns(2)
    with c4:
        f_op = st.date_input("Fecha:", value=dt_val.date(), key=f"dlg_date_{op_id}")
        h_op = st.time_input("Hora:", value=dt_val.time(), key=f"dlg_time_{op_id}")
        dt_manual = datetime.combine(f_op, h_op)
    with c5:
        nota_init = str(op.get("nota", "")).strip() if pd.notna(op.get("nota")) and str(op.get("nota")).lower() != "none" else ""
        m_nota = st.text_input("Nota / Referencia:", value=nota_init, key=f"dlg_nota_{op_id}")

    total_fiat = round(m_usdt * m_tasa, 2)
    if st.session_state.get("cfg_redondear_pagos", True) and trade_code == "BUY":
        total_fiat = math.ceil(total_fiat)

    st.info(f"💵 **Total Calculado:** {total_fiat:,.2f} {FIAT_CURRENCY}")

    col_save, col_cancel = st.columns([1, 1])
    with col_save:
        if st.button("Guardar Cambios 💾", type="primary", use_container_width=True, key=f"dlg_btn_save_{op_id}"):
            if m_usdt > 0 and m_tasa > 0:
                datos_actualizados = {
                    "Fecha_Hora": dt_manual.strftime("%Y-%m-%d %H:%M:%S"),
                    "tradeType": trade_code,
                    "amount": m_usdt,
                    "unitPrice": m_tasa,
                    "totalPrice": total_fiat,
                    "nota": m_nota.strip()
                }
                ok = data_manager.actualizar_operacion_manual(op_id, datos_actualizados)
                if ok:
                    st.success("✅ Operación actualizada exitosamente.")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("❌ Error al guardar en base de datos.")
            else:
                st.error("Ingresa montos válidos mayores a cero.")

    with col_cancel:
        if st.button("Cancelar", use_container_width=True, key=f"dlg_btn_cancel_{op_id}"):
            st.rerun()


@st.dialog("🗑️ Confirmar Eliminación")
def eliminar_operacion_dialog(op: dict):
    op_id = str(op["id"])
    st.warning(f"¿Estás seguro de que deseas eliminar permanentemente la operación **#{op_id}**?")

    t_type = str(op.get("tradeType", "SELL")).upper()
    m_usdt = float(op.get("amount", 0.0))
    m_tasa = float(op.get("unitPrice", 0.0))
    m_total = float(op.get("totalPrice", 0.0))
    f_h = str(op.get("Fecha_Hora", ""))
    nota = str(op.get("nota", "")).strip() if pd.notna(op.get("nota")) and str(op.get("nota")).lower() != "none" else ""
    usr = str(op.get("Usuario", "Victoria")).strip()

    st.markdown(f"""
    - **Operador:** `{usr}`
    - **Tipo:** `{t_type}`
    - **Monto:** `{m_usdt:,.2f} USDT`
    - **Tasa:** `{m_tasa:,.3f} {FIAT_CURRENCY}`
    - **Total {FIAT_CURRENCY}:** `{m_total:,.2f} {FIAT_CURRENCY}`
    - **Fecha / Hora:** `{f_h}`
    {f"- **Nota:** {nota}" if nota else ""}
    """)
    st.caption("⚠️ Esta acción no se puede deshacer y se sincronizará con la base de datos.")

    col_del, col_cancel = st.columns([1, 1])
    with col_del:
        if st.button("Sí, Eliminar 🗑️", type="primary", use_container_width=True, key=f"dlg_btn_del_{op_id}"):
            ok = data_manager.eliminar_operacion_manual(op_id)
            if ok:
                st.success("🗑️ Operación eliminada correctamente.")
                time.sleep(0.4)
                st.rerun()
            else:
                st.error("❌ Error al eliminar la operación.")

    with col_cancel:
        if st.button("Cancelar", use_container_width=True, key=f"dlg_btn_del_cancel_{op_id}"):
            st.rerun()


def render_vista():
    st.title("➕ Registrar Operación Externa")
    st.caption("Para transacciones directas, Binance Pay o acuerdos OTC fuera de Binance P2P.")

    usuario_activo = st.session_state.get("usuario_activo", {"username": "Victoria", "nombre": "Victoria", "role": "operador"})
    es_admin = usuario_activo.get("role") == "admin"

    with st.form("form_registro_manual", clear_on_submit=True):
        st.write("#### 📝 Nueva Transacción Directa")
        if es_admin:
            st.caption(f"Registrando operación como Administrador: **{usuario_activo['nombre']}**")
        else:
            st.caption(f"Registrando operación para: **{usuario_activo['nombre']}**")

        c1, c2, c3 = st.columns(3)
        with c1:
            trade_type_ui = st.selectbox("Tipo de Operación:", ["Venta Externa (SELL)", "Compra Externa (BUY)"])
            trade_code = "SELL" if "SELL" in trade_type_ui else "BUY"
        with c2:
            m_usdt = st.number_input("Monto en USDT:", min_value=0.0, step=10.0, format="%.2f")
        with c3:
            m_tasa = st.number_input(f"Tasa de Cambio ({FIAT_CURRENCY}):", min_value=0.0, step=0.1, format="%.3f")

        c4, c5 = st.columns(2)
        with c4:
            f_op = st.date_input("Fecha:", value=data_manager.get_now_local().date(), key="op_ext_date")
            h_op = st.time_input("Hora:", value=data_manager.get_now_local().time(), key="op_ext_time")
            dt_manual = datetime.combine(f_op, h_op)
        with c5:
            m_nota = st.text_input("Nota / Referencia:", placeholder="Ej. Venta a cliente frecuente por Pago Móvil")

        btn_guardar = st.form_submit_button("Guardar Operación 💾", type="primary", use_container_width=True)

        if btn_guardar:
            if m_usdt > 0 and m_tasa > 0:
                total_fiat = round(m_usdt * m_tasa, 2)
                if st.session_state.get("cfg_redondear_pagos", True) and trade_code == "BUY":
                    total_fiat = math.ceil(total_fiat)

                nuevo_registro = {
                    "id": f"EXT-{int(time.time())}",
                    "Fecha_Hora": dt_manual.strftime("%Y-%m-%d %H:%M:%S"),
                    "tradeType": trade_code,
                    "amount": m_usdt,
                    "unitPrice": m_tasa,
                    "totalPrice": total_fiat,
                    "commission": 0.0,
                    "fiat": FIAT_CURRENCY,
                    "nota": m_nota,
                    "orderStatus": "COMPLETED",
                    "Usuario": usuario_activo["username"]
                }

                data_manager.guardar_operacion_manual(nuevo_registro)
                st.success(f"✅ Guardado: {trade_code} {m_usdt:,.2f} USDT a tasa {m_tasa:,.3f} {FIAT_CURRENCY} ({usuario_activo['username']}).")
            else:
                st.error("Ingresa montos válidos mayores a cero.")

    st.divider()

    df_man_raw = data_manager.get_todas_operaciones_manuales()
    df_man_view = data_manager.enriquecer_operaciones_fechas(df_man_raw)

    usuarios_existentes = sorted([str(u).strip() for u in df_man_view["Usuario"].dropna().unique() if str(u).strip()]) if not df_man_view.empty and "Usuario" in df_man_view.columns else []
    opciones_admin = ["🌐 Todos los Operadores"] + usuarios_existentes

    # Rango de la semana en curso (Lunes a Domingo)
    lunes_act, domingo_act, label_act = data_manager.get_rango_semana_actual()
    key_actual = lunes_act.strftime("%Y-%m-%d")

    semanas_dict = {
        key_actual: f"🌟 Semana Actual ({lunes_act.strftime('%d/%m')} al {domingo_act.strftime('%d/%m/%Y')})"
    }

    if not df_man_view.empty and "Lunes_Semana" in df_man_view.columns:
        df_valid = df_man_view.dropna(subset=["Lunes_Semana"]).sort_values("Lunes_Semana", ascending=False)
        for _, row in df_valid.drop_duplicates(subset=["Semana_Key"]).iterrows():
            k = row["Semana_Key"]
            if k != key_actual and row["Lunes_Semana"]:
                l_d = row["Lunes_Semana"]
                d_d = row["Domingo_Semana"]
                semanas_dict[k] = f"📁 Semana del {l_d.strftime('%d/%m')} al {d_d.strftime('%d/%m/%Y')}"

    opciones_keys = list(semanas_dict.keys())

    filtro_op = "🌐 Todos los Operadores"
    if es_admin:
        col_op, col_sem = st.columns([1.2, 1.4])
        with col_op:
            filtro_op = st.selectbox("👤 Filtrar por Operador:", opciones_admin, key="flt_op_externa_admin")
        with col_sem:
            semana_sel_key = st.selectbox(
                "📅 Período Semanal:",
                options=opciones_keys,
                format_func=lambda k: semanas_dict.get(k, k),
                index=0,
                key="sel_semana_op_ext"
            )
    else:
        col_sem = st.container()
        with col_sem:
            semana_sel_key = st.selectbox(
                "📅 Período Semanal:",
                options=opciones_keys,
                format_func=lambda k: semanas_dict.get(k, k),
                index=0,
                key="sel_semana_op_ext"
            )

    # Filtrar por operador
    df_filtered = df_man_view.copy() if not df_man_view.empty else pd.DataFrame()
    if es_admin and filtro_op != "🌐 Todos los Operadores" and not df_filtered.empty:
        df_filtered = df_filtered[df_filtered["Usuario"].astype(str).str.strip().str.lower() == filtro_op.lower()]
    elif not es_admin and not df_filtered.empty:
        df_filtered = df_filtered[df_filtered["Usuario"].astype(str).str.strip().str.lower() == usuario_activo["username"].strip().lower()]

    # Filtrar por semana
    if not df_filtered.empty and "Semana_Key" in df_filtered.columns:
        df_sem = df_filtered[df_filtered["Semana_Key"] == semana_sel_key].copy()
    else:
        df_sem = pd.DataFrame()

    now_local = data_manager.get_now_local()
    nombres_dias = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    dia_hoy_nombre = nombres_dias.get(now_local.weekday(), "Jueves")

    # Control de cambio de semana seleccionada
    last_semana = st.session_state.get("_oe_last_semana_key")
    if last_semana != semana_sel_key:
        st.session_state["_oe_last_semana_key"] = semana_sel_key
        if semana_sel_key == key_actual:
            st.session_state["filtro_dia_op_ext"] = dia_hoy_nombre
        else:
            st.session_state["filtro_dia_op_ext"] = "TODOS"

    # Predeterminar el día actual si estamos en la semana en curso y no se ha definido filtro
    if semana_sel_key == key_actual and (st.session_state.get("filtro_dia_op_ext") is None):
        st.session_state["filtro_dia_op_ext"] = dia_hoy_nombre

    filtro_estado = st.session_state.get("filtro_dia_op_ext")
    if filtro_estado == "TODOS":
        filtro_dia = None
    elif filtro_estado is not None:
        filtro_dia = filtro_estado
    elif semana_sel_key == key_actual:
        filtro_dia = dia_hoy_nombre
        st.session_state["filtro_dia_op_ext"] = dia_hoy_nombre
    else:
        filtro_dia = None

    DIAS_MAP = [
        ("Lunes", "lunes"),
        ("Martes", "martes"),
        ("Miércoles", "miercoles"),
        ("Jueves", "jueves"),
        ("Viernes", "viernes"),
        ("Sábado", "sabado"),
        ("Domingo", "domingo"),
    ]

    st.write("#### 📅 Resumen Diario de Rendimiento")

    cards_html = []
    for dia, slug in DIAS_MAP:
        sub_dia = df_sem[df_sem["Dia_Semana"] == dia] if not df_sem.empty else pd.DataFrame()
        sub_ventas = sub_dia[sub_dia["tradeType"].astype(str).str.upper() == "SELL"] if not sub_dia.empty else pd.DataFrame()
        monto_ventas_dia = sub_ventas["amount"].sum() if not sub_ventas.empty else 0.0
        cant_ventas = len(sub_ventas)
        has_sales = (cant_ventas > 0)
        is_selected = (dia == filtro_dia)

        cls_parts = ["metric-day-card"]
        if has_sales:
            cls_parts.append("has-profit")
        if is_selected:
            cls_parts.append("is-selected")
        cls_card = " ".join(cls_parts)

        color_val = "#3fb950" if has_sales else "#f0f6fc"
        badge_ventas = f"{cant_ventas} ventas" if cant_ventas != 1 else "1 venta"

        cards_html.append(
            f'<div class="{cls_card}" data-dia="{dia}" data-dia-slug="{slug}" role="button" tabindex="0" '
            f'onclick="(function(btnKey, dName){{'
            f' if (!window._lastDayClick || Date.now() - window._lastDayClick > 400) {{'
            f'   window._lastDayClick = Date.now();'
            f'   var b = document.querySelector(\'.st-key-\' + btnKey + \' button\') || '
            f'           Array.from(document.querySelectorAll(\'button\')).find(function(x){{ return (x.textContent||\'\').includes(\'Filtro_\' + dName); }});'
            f'   if (b) {{ b.click(); }}'
            f' }}'
            f'}})(\'btn_flt_op_day_{slug}\', \'{dia}\')">'
            f'<div class="metric-day-header">{dia}</div>'
            f'<div class="metric-day-val" style="color:{color_val};">{monto_ventas_dia:,.2f}</div>'
            f'<div class="metric-day-sub">{badge_ventas}</div>'
            f'</div>'
        )

    grid_html = f'<div class="days-grid-container">{"".join(cards_html)}</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    # Botones técnicos de filtro activados mediante clic en las tarjetas (ocultos vía CSS)
    for dia, slug in DIAS_MAP:
        if st.button(f"Filtro_{dia}", key=f"btn_flt_op_day_{slug}", help="tecnico_filtro"):
            if filtro_dia == dia:
                st.session_state["filtro_dia_op_ext"] = "TODOS"
            else:
                st.session_state["filtro_dia_op_ext"] = dia
            st.rerun()

    st.divider()
    st.write("#### 📋 Operaciones Manuales Registradas")

    if df_sem.empty:
        st.info(f"ℹ️ Aún no tienes operaciones registradas para {semanas_dict.get(semana_sel_key, 'esta semana')}.")
    else:
        df_cards = df_sem.sort_values("Fecha_Hora", ascending=False)
        if filtro_dia:
            df_cards = df_cards[df_cards["Dia_Semana"] == filtro_dia]
            sub_v_dia = df_cards[df_cards["tradeType"].astype(str).str.upper() == "SELL"]
            m_v_dia = sub_v_dia["amount"].sum() if not sub_v_dia.empty else 0.0
            c_v_dia = len(sub_v_dia)

            col_fb1, col_fb2 = st.columns([0.76, 0.24])
            with col_fb1:
                cls_p = "has-profit" if c_v_dia > 0 else ""
                txt_ventas = f"{c_v_dia} {'venta' if c_v_dia == 1 else 'ventas'} &bull; {m_v_dia:,.2f} USDT"
                st.html(f"""
                <div class="filtro-activo-bar {cls_p}">
                    <div class="filtro-activo-text">
                        📅 Mostrando operaciones de: <strong style="color: #58a6ff;">{filtro_dia}</strong>
                        <span style="color: #8b949e; font-size: 0.82rem; margin-left: 6px;">({txt_ventas})</span>
                    </div>
                </div>
                """)
            with col_fb2:
                if st.button("Ver todos los días ✕", key="btn_clear_op_dia_filter", type="secondary", use_container_width=True):
                    st.session_state["filtro_dia_op_ext"] = "TODOS"
                    st.rerun()

            if df_cards.empty:
                st.info(f"ℹ️ No se registraron operaciones el día {filtro_dia}. Haz clic en 'Ver todos los días ✕' o presiona otro día.")

        if not df_cards.empty:
            for _, r in df_cards.iterrows():
                op_dict = r.to_dict()
                op_id = str(r["id"])
                f_h = str(r["Fecha_Hora"])
                t_type = str(r.get("tradeType", "SELL")).upper()
                m_usdt = float(r.get("amount", 0.0))
                tasa = float(r.get("unitPrice", 0.0))
                m_total = float(r.get("totalPrice", 0.0))
                com = float(r.get("commission", 0.0))
                fiat = str(r.get("fiat", FIAT_CURRENCY))
                nota = str(r.get("nota", "")).strip() if pd.notna(r.get("nota")) else ""
                status = str(r.get("orderStatus", "COMPLETED"))
                op_usr = str(r.get("Usuario", "Victoria")).strip()

                puede_gestionar = es_admin or (op_usr.lower() == usuario_activo["username"].strip().lower())

                if "SELL" in t_type:
                    cls_trade = "sell"
                    badge_style = "background: rgba(56, 139, 253, 0.2); color: #58a6ff; border: 1px solid rgba(56, 139, 253, 0.4);"
                    amount_color = "#58a6ff"
                    fiat_badge_style = "background: rgba(56, 139, 253, 0.15); color: #58a6ff;"
                    tipo_label = "SELL"
                else:
                    cls_trade = "buy"
                    badge_style = "background: rgba(46, 160, 67, 0.2); color: #3fb950; border: 1px solid rgba(46, 160, 67, 0.4);"
                    amount_color = "#3fb950"
                    fiat_badge_style = "background: rgba(46, 160, 67, 0.15); color: #3fb950;"
                    tipo_label = "BUY"

                badge_usr_html = f'<span style="background: rgba(139, 148, 158, 0.15); color: #c9d1d9; border: 1px solid rgba(139, 148, 158, 0.3); border-radius: 12px; font-size: 0.72rem; padding: 2px 8px; font-weight: 500;">👤 {op_usr}</span>' if es_admin else ""

                with st.container(border=True):
                    st.html(f"""
                    <div class="cycle-card-content {cls_trade}">
                        <div class="cycle-top-row">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <div class="cycle-badge" style="{badge_style}">{tipo_label}</div>
                                <span style="font-size: 0.78rem; color: #8b949e;">#{op_id}</span>
                                {badge_usr_html}
                            </div>
                            <div class="cycle-profit-text" style="color: {amount_color};">{m_usdt:,.2f} USDT</div>
                        </div>
                        <div class="cycle-mid-row">
                            <div>🕒 {f_h}</div>
                            <span class="cycle-pct-badge" style="{fiat_badge_style}">{m_total:,.2f} {fiat}</span>
                        </div>
                        <div class="cycle-grid">
                            <div class="cycle-cell">
                                <span class="cycle-cell-label">Tasa Acordada</span>
                                <span class="cycle-cell-value">{tasa:,.3f} {fiat}</span>
                            </div>
                            <div class="cycle-cell">
                                <span class="cycle-cell-label">Total en {fiat}</span>
                                <span class="cycle-cell-value">{m_total:,.2f}</span>
                            </div>
                            <div class="cycle-cell">
                                <span class="cycle-cell-label">Comisión</span>
                                <span class="cycle-cell-value">{com:,.2f} USDT</span>
                            </div>
                            <div class="cycle-cell">
                                <span class="cycle-cell-label">Estado</span>
                                <span class="cycle-cell-value" style="color: #3fb950;">{status}</span>
                            </div>
                        </div>
                    </div>
                    """)

                    html_nota_inner = f'<span>📝 Nota: <strong style="color: #f0f6fc;">{nota}</strong></span>' if nota and nota.lower() != "none" else '<span style="color: #8b949e;">📝 <em>Sin nota</em></span>'

                    if puede_gestionar:
                        col_nota, col_edit, col_del = st.columns([0.84, 0.08, 0.08])
                        with col_nota:
                            st.html(f"""
                            <div class="cycle-inner-ajuste-pill">
                                {html_nota_inner}
                            </div>
                            """)
                        with col_edit:
                            if st.button("✏️", key=f"btn_edit_{op_id}", type="secondary", help=f"Editar operación #{op_id}"):
                                editar_operacion_dialog(op_dict)
                        with col_del:
                            if st.button("🗑️", key=f"btn_del_{op_id}", type="secondary", help=f"Eliminar operación #{op_id}"):
                                eliminar_operacion_dialog(op_dict)
                    else:
                        st.html(f"""
                        <div class="cycle-inner-ajuste-pill" style="border-top: 1px dashed #30363d; margin-top: 14px; padding-top: 10px;">
                            {html_nota_inner}
                        </div>
                        """)