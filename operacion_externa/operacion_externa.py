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

    with st.form("form_operacion_externa", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            m_tipo = st.selectbox("Tipo de Operación", ["SELL (Venta)", "BUY (Compra)"])
            m_fecha = st.date_input("Fecha", value=data_manager.get_now_local().date())
            st.write("**Hora de la Operación:**")
            col_mh, col_mm, col_mp = st.columns(3)
            mh_val = col_mh.selectbox("Hora", HORAS_12, index=8)
            mm_val = col_mm.selectbox("Minuto", MINUTOS, index=0)
            mp_val = col_mp.selectbox("Periodo", PERIODOS, index=0)

        with c2:
            m_usdt = st.number_input("Monto en USDT", min_value=0.0, step=50.0, format="%.2f")
            m_tasa = st.number_input(f"Tasa acordada ({FIAT_CURRENCY})", min_value=0.0, step=0.10, format="%.3f")
            m_nota = st.text_input("Nota / Contraparte / Referencia", placeholder="Ej: Venta Binance Pay a Pedro")

        btn_guardar = st.form_submit_button("Guardar Operación", type="primary", use_container_width=True)

        if btn_guardar:
            if m_usdt > 0 and m_tasa > 0:
                dt_manual = convertir_a_datetime(m_fecha, mh_val, mm_val, mp_val)
                trade_code = "SELL" if "SELL" in m_tipo else "BUY"
                total_fiat = m_usdt * m_tasa
                if st.session_state["cfg_redondear_pagos"] and trade_code == "BUY":
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
                    "orderStatus": "COMPLETED"
                }

                data_manager.guardar_operacion_manual(nuevo_registro)
                st.success(f"✅ Guardado: {trade_code} {m_usdt:,.2f} USDT a tasa {m_tasa:,.3f} {FIAT_CURRENCY}.")
            else:
                st.error("Ingresa montos válidos mayores a cero.")

    st.divider()
    st.write("#### 📋 Operaciones Manuales Registradas")
    df_man_view = data_manager.get_todas_operaciones_manuales()
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