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
    if not es_admin and not df_man_view.empty and "Usuario" in df_man_view.columns:
        df_man_view = df_man_view[df_man_view["Usuario"].astype(str).str.lower() == usuario_activo["username"].lower()]
    if not df_man_view.empty:
        df_man_sorted = df_man_view.sort_values("Fecha_Hora", ascending=False)
        for _, r in df_man_sorted.iterrows():
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

            html_nota = f"""
            <div class="cycle-ajuste-pill" style="color: #8b949e;">
                <span>📝 Nota: <strong style="color: #f0f6fc;">{nota}</strong></span>
            </div>
            """ if nota and nota.lower() != "none" else ""

            st.markdown(f"""
            <div class="cycle-card-item {cls_trade}">
                <div class="cycle-top-row">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div class="cycle-badge" style="{badge_style}">{tipo_label}</div>
                        <span style="font-size: 0.78rem; color: #8b949e;">#{op_id}</span>
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
            """, unsafe_allow_html=True)
    else:
        st.info("No hay operaciones externas registradas aún.")