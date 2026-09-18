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
        if st.button("Sí, Eliminar Ciclo 🗑️", type="primary", use_container_width=True, key=f"dlg_btn_del_c_{c_num}"):
            ok = data_manager.eliminar_ciclo(c_num)
            if ok:
                st.success(f"🗑️ Ciclo #{c_num} eliminado correctamente.")
                time.sleep(0.4)
                st.rerun()
            else:
                st.error("❌ Error al eliminar el ciclo.")

    with col_cancel:
        if st.button("Cancelar", use_container_width=True, key=f"dlg_btn_del_cancel_c_{c_num}"):
            st.rerun()

@st.dialog("✏️ Editar Ciclo")
def editar_ajuste_dialog(c_num, aj_actual, u_gan_actual, cap, f_h, f_ini_val="", f_fin_val="", ret_admin_actual=0.0):
    profit_base = u_gan_actual - aj_actual
    now_local = data_manager.get_now_local()

    dt_ini_parsed = pd.to_datetime(f_ini_val, dayfirst=True, errors="coerce")
    if pd.isna(dt_ini_parsed):
        dt_ini_parsed = pd.to_datetime(f_h, dayfirst=True, errors="coerce")
    if pd.isna(dt_ini_parsed):
        dt_ini_parsed = pd.Timestamp(now_local)

    dt_fin_parsed = pd.to_datetime(f_fin_val, dayfirst=True, errors="coerce")
    if pd.isna(dt_fin_parsed):
        dt_fin_parsed = pd.to_datetime(f_h, dayfirst=True, errors="coerce")
    if pd.isna(dt_fin_parsed):
        dt_fin_parsed = pd.Timestamp(now_local)

    fechas_header = f"{f_ini_val} ➔ {f_fin_val}" if (f_ini_val and f_fin_val) else f_h

    st.markdown(f"""
    <div style="background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 12px 14px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="color: #f0f6fc; font-size: 1.05rem;">Ciclo #{c_num}</strong>
            <span style="color: #8b949e; font-size: 0.8rem;">🕒 {fechas_header}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #8b949e;">
            <span>Capital: <strong style="color: #e6edf3;">{cap:,.2f} USDT</strong></span>
            <span>Profit Base: <strong style="color: #58a6ff;">{profit_base:,.2f} USDT</strong></span>
        </div>
        <div style="margin-top: 6px; font-size: 0.85rem; color: #8b949e; display: flex; gap: 16px; flex-wrap: wrap;">
            <span>Ajuste actual: <strong style="color: {'#3fb950' if aj_actual >= 0 else '#f85149'};">{aj_actual:+.2f} USDT</strong></span>
            <span>Entregado a Admin: <strong style="color: #f59e0b;">{ret_admin_actual:,.2f} USDT</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("#### ⏱️ Modificar Horario del Ciclo")
    c_ini_box, c_fin_box = st.columns(2)
    with c_ini_box:
        st.markdown("<div style='font-size:0.85rem; font-weight:600; color:#58a6ff; margin-bottom:4px;'>🟢 Inicio:</div>", unsafe_allow_html=True)
        d_ini = st.date_input("Fecha Inicio:", value=dt_ini_parsed.date(), key=f"dlg_d_ini_{c_num}")
        t_ini = st.time_input("Hora Inicio:", value=dt_ini_parsed.time().replace(second=0, microsecond=0), key=f"dlg_t_ini_{c_num}", step=60)
    with c_fin_box:
        st.markdown("<div style='font-size:0.85rem; font-weight:600; color:#58a6ff; margin-bottom:4px;'>🔴 Fin:</div>", unsafe_allow_html=True)
        d_fin = st.date_input("Fecha Fin:", value=dt_fin_parsed.date(), key=f"dlg_d_fin_{c_num}")
        t_fin = st.time_input("Hora Fin:", value=dt_fin_parsed.time().replace(second=0, microsecond=0), key=f"dlg_t_fin_{c_num}", step=60)

    dt_ini_new = datetime.combine(d_ini, t_ini)
    dt_fin_new = datetime.combine(d_fin, t_fin)

    st.divider()

    st.write("#### ✍️ Modificar Ajuste y Dinero a Admin")
    c_e1, c_e2 = st.columns(2)
    with c_e1:
        nuevo_ajuste = st.number_input(
            "Ajuste USDT (+/-):",
            value=float(aj_actual),
            step=0.10,
            format="%.2f",
            key=f"input_modal_ajuste_{c_num}",
            help="Positivo si sobró dinero. Negativo si faltó enviar a un cliente o hubo algún gasto no reflejado."
        )
    with c_e2:
        nuevo_ret_adm = st.number_input(
            "Entregado a Admin (USDT):",
            value=float(ret_admin_actual),
            step=0.10,
            format="%.2f",
            min_value=0.0,
            key=f"input_modal_ret_adm_{c_num}",
            help="Dinero entregado al administrador durante este ciclo a reponer al final del día."
        )

    nueva_ganancia = profit_base + nuevo_ajuste
    nuevo_pct = (nueva_ganancia / cap * 100) if cap > 0 else 0.0
    dif_total = nuevo_ajuste - aj_actual

    color_res = "#3fb950" if nueva_ganancia >= 0 else "#f85149"
    badge_cls = "badge-pill-pos" if nueva_ganancia >= 0 else "badge-pill-neg"
    sign_n = "+" if nueva_ganancia >= 0 else ""
    sign_pct = "+" if nuevo_pct >= 0 else ""
    sub_info_adm = f'<div style="font-size: 0.78rem; color: #f59e0b; margin-top: 4px;">👤 Entregado a Admin: {nuevo_ret_adm:,.2f} USDT (a reponer hoy, no altera la ganancia)</div>' if nuevo_ret_adm > 0 else ''

    st.caption("Previsualización de la ganancia recalculada:")
    st.markdown(f"""
    <div style="background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
        <div style="font-size: 1.25rem; font-weight: 700; color: {color_res};">
            {sign_n}{nueva_ganancia:,.2f} USDT
            <span class="{badge_cls}" style="margin-left: 8px; font-size: 0.82rem;">{sign_pct}{nuevo_pct:.2f}%</span>
        </div>
        {sub_info_adm}
        <div style="font-size: 0.78rem; color: #8b949e; margin-top: 4px;">
            Diferencia vs previo: <strong style="color: {'#3fb950' if dif_total >= 0 else '#f85149'};">{dif_total:+.2f} USDT</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c_s1, c_s2 = st.columns(2)
    with c_s1:
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True, key=f"btn_save_aj_{c_num}"):
            if dt_ini_new >= dt_fin_new:
                st.error("⚠️ La fecha y hora de inicio debe ser anterior a la de fin.")
            else:
                str_ini = dt_ini_new.strftime("%d/%m/%Y %I:%M %p")
                str_fin = dt_fin_new.strftime("%d/%m/%Y %I:%M %p")
                str_hora = dt_fin_new.strftime("%d/%m/%Y %I:%M:%S %p")
                if data_manager.actualizar_ciclo_ajuste_y_fechas(c_num, nuevo_ajuste, str_ini, str_fin, str_hora, nuevo_retiro_admin=nuevo_ret_adm):
                    st.toast(f"✅ Ciclo #{c_num} actualizado exitosamente")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("Error al guardar los cambios del ciclo.")
    with c_s2:
        if st.button("Cancelar", type="secondary", use_container_width=True, key=f"btn_cancel_aj_{c_num}"):
            st.rerun()

def render_vista():
    st.title("📊 Histórico Semanal y Liquidación de Operador")

    df_all = data_manager.get_historico()
    df_all = data_manager.enriquecer_historico_fechas(df_all)

    usuario_activo = st.session_state.get("usuario_activo", {"username": "Victoria", "nombre": "Victoria", "role": "operador"})
    es_admin = usuario_activo.get("role") == "admin"

    if es_admin:
        st.caption(f"Panel de Liquidación &bull; Administrador: **{usuario_activo['nombre']}**")
    else:
        st.caption(f"Panel de Liquidación de **{usuario_activo['nombre']}** &bull; Cobro de 80% sobre comisión generada.")

    # Rango de la semana en curso (Lunes a Domingo)
    lunes_act, domingo_act, label_act = data_manager.get_rango_semana_actual()
    key_actual = lunes_act.strftime("%Y-%m-%d")

    # Armar opciones de semanas disponibles (de más reciente a más antigua)
    semanas_dict = {
        key_actual: f"🌟 Semana Actual ({lunes_act.strftime('%d/%m')} al {domingo_act.strftime('%d/%m/%Y')})"
    }

    if not df_all.empty and "Lunes_Semana" in df_all.columns:
        df_valid = df_all.dropna(subset=["Lunes_Semana"]).sort_values("Lunes_Semana", ascending=False)
        for _, row in df_valid.drop_duplicates(subset=["Semana_Key"]).iterrows():
            k = row["Semana_Key"]
            if k != key_actual and row["Lunes_Semana"]:
                l_d = row["Lunes_Semana"]
                d_d = row["Domingo_Semana"]
                semanas_dict[k] = f"📁 Semana del {l_d.strftime('%d/%m')} al {d_d.strftime('%d/%m/%Y')}"

    opciones_keys = list(semanas_dict.keys())

    op_sel = "🌐 Todos los Operadores"
    if es_admin:
        usuarios_registrados = auth.listar_usuarios()
        opciones_operadores = ["🌐 Todos los Operadores"] + [u["username"] for u in usuarios_registrados]
        if not df_all.empty and "Usuario" in df_all.columns:
            for u in df_all["Usuario"].dropna().unique():
                if u and u not in opciones_operadores:
                    opciones_operadores.append(u)

        col_op, col_sel_sem, col_meta, col_comision = st.columns([1.3, 1.4, 1.1, 1.2])
        with col_op:
            op_sel = st.selectbox("👤 Operador a Auditar:", opciones_operadores, index=0, key="hs_operador_sel")
        with col_sel_sem:
            semana_sel_key = st.selectbox(
                "📅 Período Semanal:",
                options=opciones_keys,
                format_func=lambda k: semanas_dict.get(k, k),
                index=0,
                key="sel_semana_historico"
            )
        with col_meta:
            meta_semanal = st.number_input("🎯 Meta Semanal (USDT):", min_value=100.0, value=2500.0, step=100.0)
        with col_comision:
            st.caption("Estructura de Comisión:")
            st.markdown(
                '<div class="comision-info-pill">'
                '<span><strong style="color: #f0f6fc;">20% Fondo</strong> &bull; 80% Operador &bull; 20% Respaldo</span>'
                '</div>',
                unsafe_allow_html=True
            )
    else:
        op_sel = usuario_activo["username"]
        col_sel_sem, col_meta, col_comision = st.columns([1.6, 1.2, 1.2])
        with col_sel_sem:
            semana_sel_key = st.selectbox(
                "📅 Período Semanal:",
                options=opciones_keys,
                format_func=lambda k: semanas_dict.get(k, k),
                index=0,
                key="sel_semana_historico"
            )
        with col_meta:
            meta_semanal = st.number_input("🎯 Meta Semanal (USDT):", min_value=100.0, value=2500.0, step=100.0)
        with col_comision:
            st.caption("Estructura de Comisión:")
            st.markdown(
                '<div class="comision-info-pill">'
                '<span><strong style="color: #f0f6fc;">20% Fondo</strong> &bull; 80% Operador &bull; 20% Respaldo</span>'
                '</div>',
                unsafe_allow_html=True
            )

    # Filtrar ciclos por operador si no es "Todos los Operadores"
    if op_sel != "🌐 Todos los Operadores":
        df_all = df_all[df_all["Usuario"].astype(str).str.lower() == op_sel.lower()]

    # Filtrar ciclos pertenecientes a la semana seleccionada
    if not df_all.empty and "Semana_Key" in df_all.columns:
        df_hist = df_all[df_all["Semana_Key"] == semana_sel_key].copy()
    else:
        df_hist = pd.DataFrame(columns=data_manager.COLUMNS_HISTORICO)

    total_ganado_semana = df_hist["USDT_Ganado"].sum() if not df_hist.empty else 0.0
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
            f'<div class="kpi-card-sub">Objetivo Lunes a Domingo</div>'
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

    now_local = data_manager.get_now_local()
    nombres_dias = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
    dia_hoy_nombre = nombres_dias.get(now_local.weekday(), "Miércoles")

    # Control de cambio de semana seleccionada
    last_semana = st.session_state.get("_hs_last_semana_key")
    if last_semana != semana_sel_key:
        st.session_state["_hs_last_semana_key"] = semana_sel_key
        if semana_sel_key == key_actual:
            st.session_state["filtro_dia_semana"] = dia_hoy_nombre
        else:
            st.session_state["filtro_dia_semana"] = "TODOS"

    # Si es la semana actual y no se ha inicializado el filtro (o se reseteó al ingresar), predeterminar el día de hoy
    if semana_sel_key == key_actual and (st.session_state.get("filtro_dia_semana") is None):
        st.session_state["filtro_dia_semana"] = dia_hoy_nombre

    filtro_estado = st.session_state.get("filtro_dia_semana")
    if filtro_estado == "TODOS":
        filtro_dia = None
    elif filtro_estado is not None:
        filtro_dia = filtro_estado
    elif semana_sel_key == key_actual:
        filtro_dia = dia_hoy_nombre
        st.session_state["filtro_dia_semana"] = dia_hoy_nombre
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

    cards_html = []
    for dia, slug in DIAS_MAP:
        sub_dia = df_hist[df_hist["Dia_Semana"] == dia] if not df_hist.empty else pd.DataFrame()
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
            f'<div class="{cls_card}" data-dia="{dia}" data-dia-slug="{slug}" role="button" tabindex="0" '
            f'onclick="(function(btnKey, dName){{'
            f' if (!window._lastDayClick || Date.now() - window._lastDayClick > 400) {{'
            f'   window._lastDayClick = Date.now();'
            f'   var b = document.querySelector(\'.st-key-\' + btnKey + \' button\') || '
            f'           Array.from(document.querySelectorAll(\'button\')).find(function(x){{ return (x.textContent||\'\').includes(\'Filtro_\' + dName); }});'
            f'   if (b) {{ b.click(); }}'
            f' }}'
            f'}})(\'btn_flt_day_{slug}\', \'{dia}\')">'
            f'<div class="metric-day-header">{dia}</div>'
            f'<div class="metric-day-val" style="color:{color_val};">{prefix}{ganado_dia:,.2f}</div>'
            f'<div class="metric-day-sub">{badge_ciclos}</div>'
            f'</div>'
        )

    grid_html = f'<div class="days-grid-container">{"".join(cards_html)}</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    # Botones técnicos de filtro activados mediante clic táctil en las tarjetas (ocultos vía CSS fuera de pantalla)
    for dia, slug in DIAS_MAP:
        if st.button(f"Filtro_{dia}", key=f"btn_flt_day_{slug}"):
            if filtro_dia == dia:
                st.session_state["filtro_dia_semana"] = "TODOS"
            else:
                st.session_state["filtro_dia_semana"] = dia
            st.rerun()

    st.divider()

    st.write("#### 📑 Histórico de Ciclos Registrados")

    if df_hist.empty:
        st.info(f"ℹ️ Aún no tienes ciclos registrados para {semanas_dict.get(semana_sel_key, 'esta semana')}.")
    else:
        df_cards = df_hist.sort_values("Ciclo", ascending=False)
        if filtro_dia:
            df_cards = df_cards[df_cards["Dia_Semana"] == filtro_dia]
            tot_ret_dia = df_cards["Retiro_Admin"].sum() if ("Retiro_Admin" in df_cards.columns and not df_cards.empty) else 0.0

            col_fb1, col_fb2 = st.columns([0.76, 0.24])
            with col_fb1:
                gan_f = df_cards["USDT_Ganado"].sum() if not df_cards.empty else 0.0
                cls_p = "has-profit" if gan_f > 0 else ""
                html_ret_dia = f'<span style="background: rgba(245, 158, 11, 0.18); border: 1px solid rgba(245, 158, 11, 0.45); padding: 2px 8px; border-radius: 4px; color: #f59e0b; font-weight: 700; margin-left: 10px; font-size: 0.80rem;">⚠️ Total a reponer hoy por Admin: {tot_ret_dia:,.2f} USDT</span>' if tot_ret_dia > 0 else ''
                st.html(f"""
                <div class="filtro-activo-bar {cls_p}">
                    <div class="filtro-activo-text">
                        📅 Mostrando ciclos de: <strong style="color: #58a6ff;">{filtro_dia}</strong>
                        <span style="color: #8b949e; font-size: 0.82rem; margin-left: 6px;">({len(df_cards)} {'ciclo' if len(df_cards) == 1 else 'ciclos'})</span>
                        {html_ret_dia}
                    </div>
                </div>
                """)
            with col_fb2:
                if st.button("Ver todos los días ✕", key="btn_clear_dia_filter", type="secondary", use_container_width=True):
                    st.session_state["filtro_dia_semana"] = "TODOS"
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
            ret_adm = float(r.get("Retiro_Admin", 0.0))

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

            pill_ret_admin = f'<div style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); padding: 2px 8px; border-radius: 4px; font-size: 0.78rem; display: inline-flex; align-items: center;"><span style="color: #f59e0b; font-weight: 600;">👤 Entregado a Admin:</span> <strong style="color: #f59e0b; margin-left: 4px;">{ret_adm:,.2f} USDT</strong></div>' if ret_adm > 0 else ''

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
                        <div class="cycle-inner-ajuste-pill" style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <span style="color: #8b949e;">⚙️ Ajuste manual:</span>
                                <strong style="color: {color_aj};">{texto_aj}</strong>
                            </div>
                            {pill_ret_admin}
                        </div>
                        """)
                    with col_ed:
                        if st.button("✏️", key=f"btn_edit_aj_{c_num}", type="secondary", help=f"Editar Ciclo #{c_num}"):
                            editar_ajuste_dialog(c_num, aj, u_gan, cap, f_h, f_ini, f_fin, ret_admin_actual=ret_adm)
                    with col_del:
                        if st.button("🗑️", key=f"btn_del_c_{c_num}", type="secondary", help=f"Eliminar Ciclo #{c_num}"):
                            eliminar_ciclo_dialog(r.to_dict())
                else:
                    col_aj, col_ed = st.columns([0.94, 0.06])
                    with col_aj:
                        st.html(f"""
                        <div class="cycle-inner-ajuste-pill" style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <span style="color: #8b949e;">⚙️ Ajuste manual:</span>
                                <strong style="color: {color_aj};">{texto_aj}</strong>
                            </div>
                            {pill_ret_admin}
                        </div>
                        """)
                    with col_ed:
                        if st.button("✏️", key=f"btn_edit_aj_{c_num}", type="secondary", help=f"Editar Ciclo #{c_num}"):
                            editar_ajuste_dialog(c_num, aj, u_gan, cap, f_h, f_ini, f_fin, ret_admin_actual=ret_adm)