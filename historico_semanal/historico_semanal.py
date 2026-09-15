import pandas as pd
import streamlit as st
import data_manager

FIAT_CURRENCY = "VES"

@st.dialog("✏️ Reacomodar Ajuste de Ciclo")
def editar_ajuste_dialog(c_num, aj_actual, u_gan_actual, cap, f_h):
    profit_base = u_gan_actual - aj_actual

    st.markdown(f"""
    <div style="background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 12px 14px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="color: #f0f6fc; font-size: 1.05rem;">Ciclo #{c_num}</strong>
            <span style="color: #8b949e; font-size: 0.8rem;">🕒 {f_h}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #8b949e;">
            <span>Capital: <strong style="color: #e6edf3;">{cap:,.2f} USDT</strong></span>
            <span>Profit Base: <strong style="color: #58a6ff;">{profit_base:,.2f} USDT</strong></span>
        </div>
        <div style="margin-top: 6px; font-size: 0.85rem; color: #8b949e;">
            Ajuste actual registrado: <strong style="color: {'#3fb950' if aj_actual >= 0 else '#f85149'};">{aj_actual:+.2f} USDT</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("#### ✍️ Modificar Ajuste")
    nuevo_ajuste = st.number_input(
        "Nuevo valor de Ajuste USDT (+/-):",
        value=float(aj_actual),
        step=0.10,
        format="%.2f",
        key=f"input_modal_ajuste_{c_num}",
        help="Positivo si sobró dinero. Negativo si faltó enviar a un cliente o hubo algún gasto no reflejado."
    )

    nueva_ganancia = profit_base + nuevo_ajuste
    nuevo_pct = (nueva_ganancia / cap * 100) if cap > 0 else 0.0
    dif_ajuste = nuevo_ajuste - aj_actual

    color_res = "#3fb950" if nueva_ganancia >= 0 else "#f85149"
    badge_cls = "badge-pill-pos" if nueva_ganancia >= 0 else "badge-pill-neg"
    sign_n = "+" if nueva_ganancia >= 0 else ""
    sign_pct = "+" if nuevo_pct >= 0 else ""

    st.caption("Previsualización de la ganancia recalculada:")
    st.markdown(f"""
    <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
        <div style="font-size: 1.25rem; font-weight: 700; color: {color_res};">
            {sign_n}{nueva_ganancia:,.2f} USDT
            <span class="{badge_cls}" style="margin-left: 8px; font-size: 0.82rem;">{sign_pct}{nuevo_pct:.2f}%</span>
        </div>
        <div style="font-size: 0.78rem; color: #8b949e; margin-top: 4px;">
            Diferencia vs ajuste previo: <strong style="color: {'#3fb950' if dif_ajuste >= 0 else '#f85149'};">{dif_ajuste:+.2f} USDT</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c_s1, c_s2 = st.columns(2)
    with c_s1:
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True, key=f"btn_save_aj_{c_num}"):
            if data_manager.actualizar_ajuste_ciclo(c_num, nuevo_ajuste):
                st.toast(f"✅ Ciclo #{c_num} actualizado a {nuevo_ajuste:+.2f} USDT")
                st.rerun()
            else:
                st.error("Error al guardar el ajuste.")
    with c_s2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"btn_cancel_aj_{c_num}"):
            st.rerun()

@st.dialog("⚠️ Confirmar Reinicio de Semana")
def confirmar_reinicio_dialog():
    st.write("¿Estás seguro de que deseas **reiniciar la semana**?")
    st.warning("⚠️ Esta acción borrará todos los ciclos registrados en el histórico actual. Esta operación no se puede deshacer.")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("🗑️ Sí, borrar todo", type="primary", use_container_width=True):
            data_manager.reiniciar_semana()
            st.toast("Semana reiniciada con éxito")
            st.rerun()
    with col_d2:
        if st.button("Cancelar", type="secondary", use_container_width=True):
            st.rerun()

def render_vista():
    st.title("📊 Histórico Semanal y Liquidación de Operador")

    col_meta1, col_meta2 = st.columns([3, 2])
    with col_meta1:
        meta_semanal = st.number_input("🎯 Meta Semanal (USDT):", min_value=100.0, value=2500.0, step=100.0)
    with col_meta2:
        st.caption("Estructura de Comisión:")
        st.markdown(
            '<div class="comision-info-pill">'
            '<span><strong style="color: #f0f6fc;">20% Fondo</strong> &bull; 80% Operador &bull; 20% Respaldo</span>'
            '</div>',
            unsafe_allow_html=True
        )

    df_hist = data_manager.get_historico()

    if not df_hist.empty:
        df_hist["Capital"] = pd.to_numeric(df_hist["Capital"], errors="coerce").fillna(0.0)
        df_hist["Ganancia_Pct"] = pd.to_numeric(df_hist["Ganancia_Pct"], errors="coerce").fillna(0.0)
        df_hist["Ajuste"] = pd.to_numeric(df_hist["Ajuste"], errors="coerce").fillna(0.0)
        df_hist["USDT_Ganado"] = pd.to_numeric(df_hist["USDT_Ganado"], errors="coerce").fillna(0.0)

        total_ganado_semana = df_hist["USDT_Ganado"].sum()
        restante_meta = total_ganado_semana - meta_semanal
        fondo_total_20 = total_ganado_semana * 0.20
        pago_operador_80 = fondo_total_20 * 0.80
        fondo_seguro_20 = fondo_total_20 * 0.20

        color_rest = "#f85149" if restante_meta < 0 else "#3fb950"
        sub_rest = "Falta para cumplir" if restante_meta < 0 else "Meta superada"
        sign_tot = "+" if total_ganado_semana >= 0 else ""

        kpis_html = [
            (
                f'<div class="kpi-card">'
                f'<div class="kpi-card-header">Meta Semanal</div>'
                f'<div class="kpi-card-val">{meta_semanal:,.2f} <span class="kpi-unit">USDT</span></div>'
                f'<div class="kpi-card-sub">Objetivo Lunes a Viernes</div>'
                f'</div>'
            ),
            (
                f'<div class="kpi-card kpi-card-restante">'
                f'<div class="kpi-card-header">Restante</div>'
                f'<div class="kpi-card-val" style="color:{color_rest};">{restante_meta:+,.2f} <span class="kpi-unit">USDT</span></div>'
                f'<div class="kpi-card-sub">{sub_rest}</div>'
                f'</div>'
            ),
            (
                f'<div class="kpi-card kpi-card-profit kpi-hero">'
                f'<div class="kpi-card-header" style="color:#7ee787;">Total USDT Ganado</div>'
                f'<div class="kpi-card-val" style="color:#3fb950;">{sign_tot}{total_ganado_semana:,.2f} <span class="kpi-unit">USDT</span></div>'
                f'<div class="kpi-card-sub">Suma de ciclos cerrados</div>'
                f'</div>'
            ),
            (
                f'<div class="kpi-card kpi-card-sell">'
                f'<div class="kpi-card-header" style="color:#79c0ff;">Pago Operador (80%)</div>'
                f'<div class="kpi-card-val" style="color:#58a6ff;">{pago_operador_80:,.2f} <span class="kpi-unit">USDT</span></div>'
                f'<div class="kpi-card-sub">80% de comisión generada</div>'
                f'</div>'
            ),
            (
                f'<div class="kpi-card kpi-card-buy">'
                f'<div class="kpi-card-header" style="color:#e3b341;">Fondo Respaldo (20%)</div>'
                f'<div class="kpi-card-val" style="color:#e3b341;">{fondo_seguro_20:,.2f} <span class="kpi-unit">USDT</span></div>'
                f'<div class="kpi-card-sub">Seguro contra pérdidas</div>'
                f'</div>'
            ),
        ]

        grid_kpis_html = f'<div class="kpis-grid-container">{"".join(kpis_html)}</div>'
        st.markdown(grid_kpis_html, unsafe_allow_html=True)

        st.divider()

        st.write("#### 📅 Resumen Diario de Rendimiento")
        df_hist["DT_Parsed"] = pd.to_datetime(df_hist["Fecha_Hora"], dayfirst=True, errors="coerce")
        nombres_dias = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
        df_hist["Dia_Semana"] = df_hist["DT_Parsed"].dt.dayofweek.map(nombres_dias)

        filtro_dia = st.session_state.get("filtro_dia_semana", None)

        dias_orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        if (df_hist["Dia_Semana"] == "Domingo").any() and "Domingo" not in dias_orden:
            dias_orden.append("Domingo")

        cards_html = []
        for dia in dias_orden:
            sub_dia = df_hist[df_hist["Dia_Semana"] == dia]
            ganado_dia = sub_dia["USDT_Ganado"].sum() if not sub_dia.empty else 0.0
            ciclos_dia = len(sub_dia)
            has_profit = ganado_dia > 0
            is_selected = (dia == filtro_dia)

            cls_parts = ["metric-day-card"]
            if has_profit:
                cls_parts.append("has-profit")
            if is_selected:
                cls_parts.append("is-selected")
            cls_card = " ".join(cls_parts)

            color_val = "#3fb950" if has_profit else "#f0f6fc"
            prefix = "+" if has_profit else ""
            badge_ciclos = f"{ciclos_dia} ciclos" if ciclos_dia != 1 else "1 ciclo"

            cards_html.append(
                f'<div class="{cls_card}" data-dia="{dia}">'
                f'<div class="metric-day-header">{dia}</div>'
                f'<div class="metric-day-val" style="color:{color_val};">{prefix}{ganado_dia:,.2f}</div>'
                f'<div class="metric-day-sub">{badge_ciclos}</div>'
                f'</div>'
            )

        grid_html = f'<div class="days-grid-container">{"".join(cards_html)}</div>'
        st.markdown(grid_html, unsafe_allow_html=True)

        # Botones técnicos de filtro activados mediante clic táctil en las tarjetas
        for d in dias_orden:
            if st.button(f"Filtro_{d}", key=f"btn_flt_day_{d}"):
                if st.session_state.get("filtro_dia_semana") == d:
                    st.session_state["filtro_dia_semana"] = None
                else:
                    st.session_state["filtro_dia_semana"] = d
                st.rerun()

        st.divider()

        st.write("#### 📑 Histórico de Ciclos Registrados")

        df_cards = df_hist.sort_values("Ciclo", ascending=False)
        if filtro_dia:
            df_cards = df_cards[df_cards["Dia_Semana"] == filtro_dia]

            col_fb1, col_fb2 = st.columns([0.76, 0.24])
            with col_fb1:
                gan_f = df_cards["USDT_Ganado"].sum() if not df_cards.empty else 0.0
                cls_p = "has-profit" if gan_f > 0 else ""
                st.markdown(f"""
                <div class="filtro-activo-bar {cls_p}">
                    <div class="filtro-activo-text">
                        📅 Mostrando ciclos de: <strong style="color: #58a6ff;">{filtro_dia}</strong>
                        <span style="color: #8b949e; font-size: 0.82rem; margin-left: 6px;">({len(df_cards)} {'ciclo' if len(df_cards) == 1 else 'ciclos'})</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col_fb2:
                if st.button("Ver todos los días ✕", key="btn_clear_dia_filter", type="secondary", use_container_width=True):
                    st.session_state["filtro_dia_semana"] = None
                    st.rerun()

            if df_cards.empty:
                st.info(f"ℹ️ No se registraron ciclos el día {filtro_dia}. Haz clic en 'Ver todos los días ✕' o presiona otro día.")
        for _, r in df_cards.iterrows():
            c_num = int(r["Ciclo"])
            f_h = str(r["Fecha_Hora"])
            u_gan = float(r["USDT_Ganado"])
            pct_g = float(r["Ganancia_Pct"])
            cap = float(r["Capital"])
            t_v = float(r["Tasa_Venta"])
            t_c = float(r["Tasa_Compra"])
            com = float(r["Comision_Pct"])
            aj = float(r.get("Ajuste", 0.0))

            cls_pos_neg = "pos" if u_gan >= 0 else "neg"
            sign = "+" if u_gan >= 0 else ""
            sign_pct = "+" if pct_g >= 0 else ""

            color_aj = "#3fb950" if aj > 0 else ("#f85149" if aj < 0 else "#8b949e")
            texto_aj = f"{aj:+.2f} USDT" if aj != 0.0 else "0.00 USDT (Sin ajuste)"

            with st.container(border=True):
                st.markdown(f"""
                <div class="cycle-card-content {cls_pos_neg}">
                    <div class="cycle-top-row">
                        <div class="cycle-badge">Ciclo #{c_num}</div>
                        <div class="cycle-profit-text {cls_pos_neg}">{sign}{u_gan:,.2f} USDT</div>
                    </div>
                    <div class="cycle-mid-row">
                        <div>🕒 {f_h}</div>
                        <span class="cycle-pct-badge {cls_pos_neg}">{sign_pct}{pct_g:.2f}%</span>
                    </div>
                    <div class="cycle-grid">
                        <div class="cycle-cell">
                            <span class="cycle-cell-label">Capital</span>
                            <span class="cycle-cell-value">{cap:,.2f} USDT</span>
                        </div>
                        <div class="cycle-cell">
                            <span class="cycle-cell-label">Comisión</span>
                            <span class="cycle-cell-value">{com:.3f}%</span>
                        </div>
                        <div class="cycle-cell">
                            <span class="cycle-cell-label">Tasa Venta</span>
                            <span class="cycle-cell-value">{t_v:,.3f} {FIAT_CURRENCY}</span>
                        </div>
                        <div class="cycle-cell">
                            <span class="cycle-cell-label">Tasa Compra</span>
                            <span class="cycle-cell-value">{t_c:,.3f} {FIAT_CURRENCY}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_aj1, col_aj2 = st.columns([0.88, 0.12])
                with col_aj1:
                    st.markdown(f"""
                    <div class="cycle-inner-ajuste-pill">
                        <span style="color: #8b949e;">⚙️ Ajuste manual:</span>
                        <strong style="color: {color_aj};">{texto_aj}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                with col_aj2:
                    if st.button("✏️", key=f"btn_edit_aj_{c_num}", type="secondary", help=f"Modificar ajuste del Ciclo #{c_num}"):
                        editar_ajuste_dialog(c_num, aj, u_gan, cap, f_h)

        col_clr1, col_clr2 = st.columns([3, 1])
        with col_clr2:
            if st.button("🗑️ Reiniciar Semana", type="secondary", use_container_width=True):
                confirmar_reinicio_dialog()
    else:
        st.info("Aún no tienes ciclos registrados en esta semana.")