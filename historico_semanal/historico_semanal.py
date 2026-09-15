import pandas as pd
import streamlit as st
import data_manager

FIAT_CURRENCY = "VES"

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

        dias_orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
        cards_html = []
        for dia in dias_orden:
            sub_dia = df_hist[df_hist["Dia_Semana"] == dia]
            ganado_dia = sub_dia["USDT_Ganado"].sum() if not sub_dia.empty else 0.0
            ciclos_dia = len(sub_dia)
            has_profit = ganado_dia > 0
            cls_card = "metric-day-card has-profit" if has_profit else "metric-day-card"
            color_val = "#3fb950" if has_profit else "#f0f6fc"
            prefix = "+" if has_profit else ""
            badge_ciclos = f"{ciclos_dia} ciclos" if ciclos_dia != 1 else "1 ciclo"

            cards_html.append(
                f'<div class="{cls_card}">'
                f'<div class="metric-day-header">{dia}</div>'
                f'<div class="metric-day-val" style="color:{color_val};">{prefix}{ganado_dia:,.2f}</div>'
                f'<div class="metric-day-sub">{badge_ciclos}</div>'
                f'</div>'
            )

        grid_html = f'<div class="days-grid-container">{"".join(cards_html)}</div>'
        st.markdown(grid_html, unsafe_allow_html=True)

        st.divider()

        st.write("#### 📑 Histórico de Ciclos Registrados")

        df_cards = df_hist.sort_values("Ciclo", ascending=False)
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

            html_ajuste = f"""
            <div class="cycle-ajuste-pill">
                <span>⚙️ Ajuste manual: <strong>{aj:+.2f} USDT</strong></span>
            </div>
            """ if aj != 0.0 else ""

            st.markdown(f"""
            <div class="cycle-card-item {cls_pos_neg}">
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
                {html_ajuste}
            </div>
            """, unsafe_allow_html=True)

        col_clr1, col_clr2 = st.columns([3, 1])
        with col_clr2:
            if st.button("🗑️ Reiniciar Semana", type="secondary", use_container_width=True):
                confirmar_reinicio_dialog()
    else:
        st.info("Aún no tienes ciclos registrados en esta semana.")