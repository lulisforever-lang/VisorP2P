import textwrap
import time
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import auth
import data_manager

FIAT_CURRENCY = "VES"

@st.dialog("🗑️ Eliminar Ciclo")
def eliminar_ciclo_dialog(ciclo_data: dict):
    c_num = int(ciclo_data["Ciclo"])
    st.warning(f"¿Estás seguro de que deseas eliminar permanentemente el **Ciclo #{c_num}**?")

    f_h = str(ciclo_data.get("Fecha_Hora", ""))
    f_ini = str(ciclo_data.get("Fecha_Inicio", "")).strip() if pd.notnull(ciclo_data.get("Fecha_Inicio")) and str(ciclo_data.get("Fecha_Inicio")).strip() not in ["", "None", "nan"] else ""
    f_fin = str(ciclo_data.get("Fecha_Fin", "")).strip() if pd.notnull(ciclo_data.get("Fecha_Fin")) and str(ciclo_data.get("Fecha_Fin")).strip() not in ["", "None", "nan"] else ""
    cap = float(ciclo_data.get("Capital", 0.0))
    u_gan = float(ciclo_data.get("USDT_Ganado", 0.0))
    pct = float(ciclo_data.get("Ganancia_Pct", 0.0))
    t_v = float(ciclo_data.get("Tasa_Venta", 0.0))
    t_c = float(ciclo_data.get("Tasa_Compra", 0.0))
    usr = str(ciclo_data.get("Usuario", "Victoria"))

    fechas_str = f"{f_ini} ➔ {f_fin}" if f_ini and f_fin else f_h

    st.markdown(f"""
    - **Ciclo:** `#{c_num}`
    - **Operador:** `{usr}`
    - **Período:** `{fechas_str}`
    - **Capital:** `{cap:,.2f} USDT`
    - **Tasa Venta:** `{t_v:,.3f} {FIAT_CURRENCY}`
    - **Tasa Compra:** `{t_c:,.3f} {FIAT_CURRENCY}`
    - **Ganancia:** `{u_gan:+,.2f} USDT ({pct:+.2f}%)`
    """)
    st.caption("⚠️ Esta acción no se puede deshacer y borrará el ciclo de la base de datos.")

    col_del, col_cancel = st.columns([1, 1])
    with col_del:
        if st.button("Sí, Eliminar Ciclo 🗑️", type="primary", use_container_width=True, key=f"dlg_btn_del_c_hg_{c_num}"):
            ok = data_manager.eliminar_ciclo(c_num)
            if ok:
                st.success(f"🗑️ Ciclo #{c_num} eliminado correctamente.")
                time.sleep(0.4)
                st.rerun()
            else:
                st.error("❌ Error al eliminar el ciclo.")

    with col_cancel:
        if st.button("Cancelar", use_container_width=True, key=f"dlg_btn_del_cancel_c_hg_{c_num}"):
            st.rerun()

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
        key=f"input_modal_ajuste_hg_{c_num}",
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
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True, key=f"btn_save_aj_hg_{c_num}"):
            if data_manager.actualizar_ajuste_ciclo(c_num, nuevo_ajuste):
                st.toast(f"✅ Ciclo #{c_num} actualizado a {nuevo_ajuste:+.2f} USDT")
                st.rerun()
            else:
                st.error("Error al guardar el ajuste.")
    with c_s2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"btn_cancel_aj_hg_{c_num}"):
            st.rerun()

def render_vista():
    st.title("📜 Historial General de Ciclos")
    df_all = data_manager.get_historico()
    df_all = data_manager.enriquecer_historico_fechas(df_all)

    usuario_activo = st.session_state.get("usuario_activo", {"username": "Victoria", "nombre": "Victoria", "role": "operador"})
    es_admin = usuario_activo.get("role") == "admin"

    if not es_admin:
        df_all = df_all[df_all["Usuario"].astype(str).str.lower() == usuario_activo["username"].lower()]
        st.caption(f"Explora y audita tu historial acumulado ({usuario_activo['nombre']}).")
    else:
        st.caption("Explora, filtra y audita todo tu historial acumulado sin restricciones temporales.")

    if df_all.empty:
        st.info("ℹ️ Aún no tienes ciclos registrados en el sistema. Los ciclos cerrados aparecerán aquí.")
        return

    # =========================================================================
    # BARRA DE FILTROS TEMPORALES Y OPERADOR
    # =========================================================================
    with st.container():
        st.write("#### 🔍 Filtros de Período y Auditoría")

        OPCIONES_FILTRO = [
            "🌐 Todo el Historial",
            "📅 Por Día Específico",
            "📆 Por Semana Específica",
            "🗓️ Por Mes Específico",
            "📈 Por Año Específico",
            "⏱️ Rango Personalizado"
        ]

        op_sel_hg = "🌐 Todos los Operadores"
        if es_admin:
            usuarios_registrados = auth.listar_usuarios()
            opciones_operadores = ["🌐 Todos los Operadores"] + [u["username"] for u in usuarios_registrados]
            if not df_all.empty and "Usuario" in df_all.columns:
                for u in df_all["Usuario"].dropna().unique():
                    if u and u not in opciones_operadores:
                        opciones_operadores.append(u)

            col_op, col_tipo, col_detalle = st.columns([1.2, 1.3, 1.8])
            with col_op:
                op_sel_hg = st.selectbox("👤 Operador:", opciones_operadores, index=0, key="hg_op_sel")
            with col_tipo:
                tipo_filtro = st.selectbox("Filtrar histórico por:", OPCIONES_FILTRO, index=0, key="hg_tipo_filtro")
        else:
            col_tipo, col_detalle = st.columns([1.5, 2.5])
            with col_tipo:
                tipo_filtro = st.selectbox("Filtrar histórico por:", OPCIONES_FILTRO, index=0, key="hg_tipo_filtro")

        if op_sel_hg != "🌐 Todos los Operadores":
            df_all = df_all[df_all["Usuario"].astype(str).str.lower() == op_sel_hg.lower()]

        df_filtrado = df_all.copy()
        label_periodo = "Todo el Historial Acumulado"

        with col_detalle:
            if tipo_filtro == "🌐 Todo el Historial":
                st.caption("Mostrando absolutamente todos los ciclos registrados.")
                label_periodo = f"Todo el Historial ({len(df_all)} ciclos)"

            elif tipo_filtro == "📅 Por Día Específico":
                fechas_disp = df_all["Fecha_Date"].dropna().unique()
                default_fecha = max(fechas_disp) if len(fechas_disp) > 0 else data_manager.get_now_local().date()
                dia_sel = st.date_input("Selecciona la fecha:", value=default_fecha, key="hg_dia_sel")
                df_filtrado = df_all[df_all["Fecha_Date"] == dia_sel]
                label_periodo = f"Día {dia_sel.strftime('%d/%m/%Y')}"

            elif tipo_filtro == "📆 Por Semana Específica":
                df_sem = df_all.dropna(subset=["Lunes_Semana"]).sort_values("Lunes_Semana", ascending=False)
                semanas_keys = df_sem["Semana_Key"].unique().tolist()
                dict_semanas = {}
                for k in semanas_keys:
                    sub = df_sem[df_sem["Semana_Key"] == k]
                    if not sub.empty:
                        r = sub.iloc[0]
                        dict_semanas[k] = f"Semana {r['Lunes_Semana'].strftime('%d/%m/%Y')} al {r['Domingo_Semana'].strftime('%d/%m/%Y')}"

                if semanas_keys:
                    sem_sel = st.selectbox(
                        "Selecciona la semana:",
                        options=semanas_keys,
                        format_func=lambda k: dict_semanas.get(k, k),
                        key="hg_semana_sel"
                    )
                    df_filtrado = df_all[df_all["Semana_Key"] == sem_sel]
                    label_periodo = dict_semanas.get(sem_sel, sem_sel)
                else:
                    st.caption("No hay semanas registradas.")

            elif tipo_filtro == "🗓️ Por Mes Específico":
                df_mes = df_all.dropna(subset=["DT_Parsed"]).sort_values("DT_Parsed", ascending=False)
                meses_keys = df_mes["Mes_Key"].unique().tolist()
                dict_meses = {}
                for k in meses_keys:
                    sub = df_mes[df_mes["Mes_Key"] == k]
                    if not sub.empty:
                        dict_meses[k] = sub.iloc[0]["Mes_Label"]

                if meses_keys:
                    mes_sel = st.selectbox(
                        "Selecciona el mes:",
                        options=meses_keys,
                        format_func=lambda k: dict_meses.get(k, k),
                        key="hg_mes_sel"
                    )
                    df_filtrado = df_all[df_all["Mes_Key"] == mes_sel]
                    label_periodo = dict_meses.get(mes_sel, mes_sel)
                else:
                    st.caption("No hay meses registrados.")

            elif tipo_filtro == "📈 Por Año Específico":
                anios_disp = sorted([int(a) for a in df_all["Anio"].dropna().unique() if a > 0], reverse=True)
                if anios_disp:
                    anio_sel = st.selectbox("Selecciona el año:", anios_disp, key="hg_anio_sel")
                    df_filtrado = df_all[df_all["Anio"] == anio_sel]
                    label_periodo = f"Año {anio_sel}"
                else:
                    st.caption("No hay años registrados.")

            elif tipo_filtro == "⏱️ Rango Personalizado":
                c_r1, c_r2 = st.columns(2)
                with c_r1:
                    f_desde = st.date_input("Desde:", value=data_manager.get_now_local().date() - timedelta(days=30), key="hg_rango_desde")
                with c_r2:
                    f_hasta = st.date_input("Hasta:", value=data_manager.get_now_local().date(), key="hg_rango_hasta")

                df_filtrado = df_all[(df_all["Fecha_Date"] >= f_desde) & (df_all["Fecha_Date"] <= f_hasta)]
                label_periodo = f"Del {f_desde.strftime('%d/%m/%Y')} al {f_hasta.strftime('%d/%m/%Y')}"

    st.divider()

    # =========================================================================
    # KPIS DEL PERÍODO FILTRADO
    # =========================================================================
    total_ganado = df_filtrado["USDT_Ganado"].sum() if not df_filtrado.empty else 0.0
    total_ciclos = len(df_filtrado)
    capital_total = df_filtrado["Capital"].sum() if not df_filtrado.empty else 0.0
    promedio_ciclo = (total_ganado / total_ciclos) if total_ciclos > 0 else 0.0
    pct_promedio = df_filtrado["Ganancia_Pct"].mean() if not df_filtrado.empty else 0.0
    
    fondo_comision_20 = total_ganado * 0.20
    pago_operador_80 = fondo_comision_20 * 0.80
    fondo_respaldo_20 = fondo_comision_20 * 0.20

    sign_tot = "+" if total_ganado >= 0 else ""
    color_ganado = "#3fb950" if total_ganado >= 0 else "#f85149"

    st.markdown(f"""
    <div class="hg-banner-periodo">
        <span>Filtro Activo: <strong style="color: #58a6ff;">{label_periodo}</strong></span>
        <span class="hg-badge-count">{total_ciclos} {'ciclo' if total_ciclos == 1 else 'ciclos'}</span>
    </div>
    """, unsafe_allow_html=True)

    kpis_html = [
        (
            f'<div class="kpi-card kpi-card-profit kpi-hero">'
            f'<div class="kpi-card-header" style="color:#7ee787;">Total USDT Ganado</div>'
            f'<div class="kpi-card-val" style="color:{color_ganado};">{sign_tot}{total_ganado:,.2f} <span class="kpi-unit">USDT</span></div>'
            f'<div class="kpi-card-sub">Resultado neto del período</div>'
            f'</div>'
        ),
        (
            f'<div class="kpi-card">'
            f'<div class="kpi-card-header">Total Ciclos</div>'
            f'<div class="kpi-card-val">{total_ciclos}</div>'
            f'<div class="kpi-card-sub">Ciclos completados</div>'
            f'</div>'
        ),
        (
            f'<div class="kpi-card">'
            f'<div class="kpi-card-header">Promedio / Ciclo</div>'
            f'<div class="kpi-card-val">{promedio_ciclo:+,.2f} <span class="kpi-unit">USDT</span></div>'
            f'<div class="kpi-card-sub">{pct_promedio:+.2f}% promedio</div>'
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
            f'<div class="kpi-card-val" style="color:#e3b341;">{fondo_respaldo_20:,.2f} <span class="kpi-unit">USDT</span></div>'
            f'<div class="kpi-card-sub">Seguro acumulado</div>'
            f'</div>'
        ),
    ]

    st.markdown(f'<div class="kpis-grid-container">{"".join(kpis_html)}</div>', unsafe_allow_html=True)

    st.divider()

    # =========================================================================
    # LISTADO DE CICLOS DEL PERÍODO
    # =========================================================================
    col_hdr1, col_hdr2 = st.columns([0.75, 0.25])
    with col_hdr1:
        st.write("#### 📑 Detalle de Ciclos Registrados")
    with col_hdr2:
        if not df_filtrado.empty:
            csv_data = df_filtrado.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Exportar CSV",
                data=csv_data,
                file_name=f"historico_ciclos_{tipo_filtro.replace(' ', '_').lower()}.csv",
                mime="text/csv",
                use_container_width=True
            )

    if df_filtrado.empty:
        st.info("ℹ️ No se encontraron ciclos registrados para el período seleccionado.")
        return

    df_cards = df_filtrado.sort_values("Ciclo", ascending=False)
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
        usr_ciclo = str(r.get("Usuario", "Victoria"))
        badge_usr = f'<span class="cycle-badge" style="margin-left: 6px; background: #21262d; color: #58a6ff;">👤 {usr_ciclo}</span>' if es_admin else ""

        f_ini = str(r.get("Fecha_Inicio", "")).strip() if pd.notnull(r.get("Fecha_Inicio")) and str(r.get("Fecha_Inicio")).strip() not in ["", "None", "nan"] else ""
        f_fin = str(r.get("Fecha_Fin", "")).strip() if pd.notnull(r.get("Fecha_Fin")) and str(r.get("Fecha_Fin")).strip() not in ["", "None", "nan"] else ""

        if f_ini and f_fin:
            html_fechas = f'🕒 <span style="color:#8b949e;">Inicio:</span> <strong style="color:#e6edf3;">{f_ini}</strong> &nbsp;<span style="color:#58a6ff;">➔</span>&nbsp; <span style="color:#8b949e;">Fin:</span> <strong style="color:#e6edf3;">{f_fin}</strong>'
        elif f_fin:
            html_fechas = f'🕒 <span style="color:#8b949e;">Fin:</span> <strong style="color:#e6edf3;">{f_fin}</strong>'
        else:
            html_fechas = f'🕒 <strong style="color:#e6edf3;">{f_h}</strong>'

        puede_eliminar = es_admin or (usr_ciclo.strip().lower() == usuario_activo.get("username", "").strip().lower())

        with st.container(border=True):
            st.html(f"""
            <div class="cycle-card-content {cls_pos_neg}">
                <div class="cycle-top-row">
                    <div style="display: flex; align-items: center;">
                        <div class="cycle-badge">Ciclo #{c_num}</div>
                        {badge_usr}
                    </div>
                    <div class="cycle-profit-text {cls_pos_neg}">{sign}{u_gan:,.2f} USDT</div>
                </div>
                <div class="cycle-mid-row">
                    <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 4px;">
                        {html_fechas}
                    </div>
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
            """)

            if puede_eliminar:
                col_aj, col_ed, col_del = st.columns([0.88, 0.06, 0.06])
                with col_aj:
                    st.html(f"""
                    <div class="cycle-inner-ajuste-pill">
                        <span style="color: #8b949e;">⚙️ Ajuste manual:</span>
                        <strong style="color: {color_aj};">{texto_aj}</strong>
                    </div>
                    """)
                with col_ed:
                    if st.button("✏️", key=f"btn_edit_aj_gen_{c_num}", type="secondary", help=f"Modificar ajuste del Ciclo #{c_num}"):
                        editar_ajuste_dialog(c_num, aj, u_gan, cap, f_h)
                with col_del:
                    if st.button("🗑️", key=f"btn_del_c_hg_{c_num}", type="secondary", help=f"Eliminar Ciclo #{c_num}"):
                        eliminar_ciclo_dialog(r.to_dict())
            else:
                col_aj, col_ed = st.columns([0.94, 0.06])
                with col_aj:
                    st.html(f"""
                    <div class="cycle-inner-ajuste-pill">
                        <span style="color: #8b949e;">⚙️ Ajuste manual:</span>
                        <strong style="color: {color_aj};">{texto_aj}</strong>
                    </div>
                    """)
                with col_ed:
                    if st.button("✏️", key=f"btn_edit_aj_gen_{c_num}", type="secondary", help=f"Modificar ajuste del Ciclo #{c_num}"):
                        editar_ajuste_dialog(c_num, aj, u_gan, cap, f_h)
