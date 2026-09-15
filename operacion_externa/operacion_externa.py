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
    st.write("#### 📋 Operaciones Manuales Registradas")
    df_man_view = data_manager.get_todas_operaciones_manuales()

    if es_admin and not df_man_view.empty and "Usuario" in df_man_view.columns:
        usuarios_existentes = sorted([str(u).strip() for u in df_man_view["Usuario"].dropna().unique() if str(u).strip()])
        opciones_admin = ["🌐 Todos los Operadores"] + usuarios_existentes
        filtro_op = st.selectbox("👤 Filtrar por Operador:", opciones_admin, key="flt_op_externa_admin")
        if filtro_op != "🌐 Todos los Operadores":
            df_man_view = df_man_view[df_man_view["Usuario"].astype(str).str.strip().str.lower() == filtro_op.lower()]
    elif not es_admin and not df_man_view.empty and "Usuario" in df_man_view.columns:
        df_man_view = df_man_view[df_man_view["Usuario"].astype(str).str.strip().str.lower() == usuario_activo["username"].strip().lower()]

    if not df_man_view.empty:
        df_man_sorted = df_man_view.sort_values("Fecha_Hora", ascending=False)
        for _, r in df_man_sorted.iterrows():
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

            html_nota = f"""
            <div class="cycle-ajuste-pill" style="color: #8b949e;">
                <span>📝 Nota: <strong style="color: #f0f6fc;">{nota}</strong></span>
            </div>
            """ if nota and nota.lower() != "none" else ""

            card_html = f"""
            <div class="cycle-card-item {cls_trade}" style="margin-bottom: {'4px' if puede_gestionar else '12px'};">
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
                {html_nota}
            </div>
            """
            st.html(card_html)

            if puede_gestionar:
                c_space, c_edit, c_del = st.columns([0.50, 0.25, 0.25])
                with c_edit:
                    if st.button("✏️ Editar", key=f"btn_edit_{op_id}", use_container_width=True):
                        editar_operacion_dialog(op_dict)
                with c_del:
                    if st.button("🗑️ Eliminar", key=f"btn_del_{op_id}", use_container_width=True):
                        eliminar_operacion_dialog(op_dict)
                st.write("")
    else:
        st.info("No hay operaciones externas registradas aún.")