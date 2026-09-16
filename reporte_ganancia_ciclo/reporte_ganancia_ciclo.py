import hashlib
import hmac
import math
import os
import time
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import requests
import streamlit as st
import auth
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

def get_binance_server_time():
    for base in ["https://api.binance.com", "https://api1.binance.com", "https://api3.binance.com"]:
        try:
            r = requests.get(f"{base}/api/v3/time", timeout=4).json()
            if "serverTime" in r:
                return int(r["serverTime"])
        except Exception:
            continue
    return int(time.time() * 1000)

def fetch_orders(api_key, api_secret, start_ms, end_ms):
    todas = []
    error_msg = None

    local_ms = int(time.time() * 1000)
    server_ms = get_binance_server_time()
    offset_ms = server_ms - local_ms

    for t_type in ["BUY", "SELL"]:
        page = 1
        while True:
            current_ts = int(time.time() * 1000) + offset_ms
            params = {
                "tradeType": t_type,
                "startTimestamp": start_ms,
                "endTimestamp": end_ms,
                "page": page,
                "rows": 50,
                "timestamp": current_ts,
                "recvWindow": 60000
            }
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            sig = hmac.new(api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
            
            resp_json = None
            last_err = None
            for base_url in ["https://api.binance.com", "https://api1.binance.com", "https://api3.binance.com"]:
                url = f"{base_url}/sapi/v1/c2c/orderMatch/listUserOrderHistory?{query_string}&signature={sig}"
                try:
                    r = requests.get(url, headers={"X-MBX-APIKEY": api_key}, timeout=15)
                    if r.status_code == 200:
                        try:
                            resp_json = r.json()
                            break
                        except Exception as e:
                            last_err = f"Error decodificando JSON: {str(e)}"
                    else:
                        try:
                            err_body = r.json()
                            last_err = f"HTTP {r.status_code}: [{err_body.get('code')}] {err_body.get('msg', r.text[:200])}"
                        except Exception:
                            last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                except Exception as e:
                    last_err = f"Fallo de conexión ({base_url}): {str(e)}"
                    continue

            if not resp_json:
                if not error_msg:
                    error_msg = last_err or "No se pudo conectar a los servidores de Binance."
                break

            code = resp_json.get("code")
            if code != "000000":
                msg = resp_json.get("msg") or resp_json.get("message") or str(resp_json)
                error_msg = f"[{code}] {msg}"
                break

            data = resp_json.get("data", [])
            if not data:
                break

            todas.extend(data)
            page += 1
            if page > 40:
                break

    return todas, error_msg

def procesar_ordenes(orders, start_dt, end_dt, redondear, incluir_pagadas):
    if not orders:
        return pd.DataFrame(), pd.DataFrame()
    df = pd.DataFrame(orders)
    if "orderNumber" in df.columns:
        df = df.drop_duplicates(subset=["orderNumber"])
    if "orderStatus" in df.columns:
        excluidos = ["CANCELLED", "CANCELLED_BY_SYSTEM", "TIMEOUT", "FAILED"]
        df = df[~df["orderStatus"].str.upper().isin(excluidos)]
        if not incluir_pagadas:
            df = df[df["orderStatus"].str.upper() == "COMPLETED"]
    if "createTime" in df.columns:
        app_tz = data_manager.get_app_timezone()
        df["Fecha_Hora"] = df["createTime"].apply(
            lambda x: datetime.fromtimestamp(x / 1000.0, tz=timezone.utc).astimezone(app_tz).replace(tzinfo=None)
        )
    df = df[(df["Fecha_Hora"] >= start_dt) & (df["Fecha_Hora"] <= end_dt)]
    for col in ["amount", "totalPrice", "unitPrice", "commission"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["totalPrice_nominal"] = df["totalPrice"]
    if redondear and "totalPrice" in df.columns:
        mask = df["tradeType"] == "BUY"
        df.loc[mask, "totalPrice"] = np.ceil(df.loc[mask, "totalPrice"])
    df["Origen"] = "Binance P2P"
    df["nota"] = df["orderNumber"].astype(str)
    cols = ["Fecha_Hora", "tradeType", "amount", "unitPrice", "totalPrice", "totalPrice_nominal", "commission", "orderStatus", "Origen", "nota"]
    b = df[df["tradeType"] == "BUY"][cols].copy() if not df.empty and (df["tradeType"] == "BUY").any() else pd.DataFrame()
    s = df[df["tradeType"] == "SELL"][cols].copy() if not df.empty and (df["tradeType"] == "SELL").any() else pd.DataFrame()
    return b, s

def get_manual(t_type, start_dt, end_dt):
    return data_manager.get_operaciones_manuales_filtradas(t_type, start_dt, end_dt)

def render_vista(api_key, api_secret):
    st.title("⚡ Reporte Ganancia Por Ciclo")
    st.subheader("⏱️ Horario Del Ciclo")

    now_local = data_manager.get_now_local()

    c_in1, c_in2, c_in3, c_in4 = st.columns([2, 1, 1, 1])
    with c_in1:
        fecha_inicio = st.date_input("Fecha Inicio", value=now_local.date(), key="f_ini")
    with c_in2:
        h_in = st.selectbox("Hora Inicio", HORAS_12, index=11, key="h_ini")
    with c_in3:
        m_in = st.selectbox("Minuto", MINUTOS, index=0, key="m_ini")
    with c_in4:
        p_in = st.selectbox("Periodo", PERIODOS, index=1, key="p_ini")

    c_fn1, c_fn2, c_fn3, c_fn4 = st.columns([2, 1, 1, 1])
    with c_fn1:
        fecha_fin = st.date_input("Fecha Fin", value=now_local.date(), key="f_fin")
    with c_fn2:
        h_fn = st.selectbox("Hora Fin", HORAS_12, index=0, key="h_fn")
    with c_fn3:
        m_fn = st.selectbox("Minuto", MINUTOS, index=20, key="m_fn")
    with c_fn4:
        p_fn = st.selectbox("Periodo", PERIODOS, index=1, key="p_fn")

    dt_inicio = convertir_a_datetime(fecha_inicio, h_in, m_in, p_in)
    dt_fin = convertir_a_datetime(fecha_fin, h_fn, m_fn, p_fn)

    st.divider()

    if st.button("Generar Reporte", type="primary", use_container_width=True):
        if not api_key or not api_secret:
            st.error("⚠️ No se encontraron las credenciales de Binance (BINANCE_API_KEY / BINANCE_API_SECRET) en Secrets ni en .env.")
        elif dt_inicio >= dt_fin:
            st.error("La fecha de inicio debe ser anterior a la de fin.")
        else:
            app_tz = data_manager.get_app_timezone()
            dt_inicio_aware = dt_inicio.replace(tzinfo=app_tz)
            dt_fin_aware = dt_fin.replace(tzinfo=app_tz)
            ts_start = int((dt_inicio_aware - timedelta(days=2)).timestamp() * 1000)
            ts_end = int((dt_fin_aware + timedelta(days=1)).timestamp() * 1000)
            with st.spinner("Conciliando ciclo..."):
                raw, err_api = fetch_orders(api_key, api_secret, ts_start, ts_end)
                if err_api:
                    st.error(f"⚠️ Error devuelto por Binance: {err_api}")
                    if "-1003" in str(err_api) or "restricted location" in str(err_api).lower() or "451" in str(err_api):
                        st.warning("🚨 **Bloqueo Geográfico de Binance:** Binance.com bloquea automáticamente los servidores ubicados en EE.UU. (como Streamlit Community Cloud en AWS Virginia).")
                mb, ms = get_manual("BUY", dt_inicio, dt_fin), get_manual("SELL", dt_inicio, dt_fin)
                if not raw and mb.empty and ms.empty and not err_api:
                    st.info("ℹ️ Conexión exitosa, pero no se encontraron órdenes en Binance ni operaciones manuales en este rango de fechas y horas.")
                bb, bs = procesar_ordenes(raw, dt_inicio, dt_fin, st.session_state["cfg_redondear_pagos"], st.session_state["cfg_incluir_pagadas"])
                df_b, df_s = pd.concat([bb, mb], ignore_index=True), pd.concat([bs, ms], ignore_index=True)

                com_v = df_s["commission"].sum() if not df_s.empty else 0.0
                com_b = df_b["commission"].sum() if not df_b.empty else 0.0
                com_tot = com_b + com_v

                # Compras (Entrada):
                # u_comp es el USDT neto recibido en billetera (descontando comisiones si aplicaron)
                u_comp = (df_b["amount"] - df_b["commission"]).sum() if not df_b.empty else 0.0
                f_gast = df_b["totalPrice"].sum() if not df_b.empty else 0.0
                f_nom = df_b["totalPrice_nominal"].sum() if not df_b.empty else 0.0
                g_red_fiat = f_gast - f_nom

                # Ventas (Salida):
                # u_vend_nom es el USDT transferido al comprador
                u_vend_nom = df_s["amount"].sum() if not df_s.empty else 0.0
                f_rec = df_s["totalPrice"].sum() if not df_s.empty else 0.0

                # u_vend_total es el USDT total que salió de la cuenta (al comprador + comisión Binance del vendedor)
                u_vend_total = u_vend_nom + com_v

                # Tasas Ponderadas Efectivas (Netas):
                t_comp = (f_gast / u_comp) if u_comp > 0 else 0.0
                t_vent = (f_rec / u_vend_total) if u_vend_total > 0 else 0.0
                t_vent_bruta = (f_rec / u_vend_nom) if u_vend_nom > 0 else 0.0

                g_red_u = (g_red_fiat / t_comp) if t_comp > 0 else 0.0
                cap_cic = min(u_comp, u_vend_nom)
                spread = ((t_vent - t_comp) / t_comp * 100) if t_comp > 0 else 0.0

                if t_comp > 0 and cap_cic > 0:
                    # Con cap_cic USDT vendidos a tasa efectiva t_vent, se obtiene fiat neto:
                    fiat_prop = cap_cic * t_vent
                    # Con ese fiat se recompran USDT a tasa efectiva t_comp:
                    u_recomp = fiat_prop / t_comp
                    profit_base = u_recomp - cap_cic
                    if st.session_state["cfg_descontar_redondeo"]:
                        profit_base -= g_red_u
                else:
                    profit_base = 0.0

                st.session_state["reporte_actual"] = {
                    "dt_inicio_str": dt_inicio.strftime('%d/%m/%Y %I:%M %p'),
                    "dt_fin_str": dt_fin.strftime('%d/%m/%Y %I:%M %p'),
                    "t_vent": t_vent,
                    "t_vent_bruta": t_vent_bruta,
                    "t_comp": t_comp,
                    "cap_cic": cap_cic,
                    "spread": spread,
                    "com_tot": com_tot,
                    "g_red_u": g_red_u,
                    "g_red_fiat": g_red_fiat,
                    "profit_base": profit_base,
                    "fecha_registro": dt_fin.strftime("%d/%m/%Y %I:%M:%S %p")
                }

    if "reporte_actual" in st.session_state:
        rep = st.session_state["reporte_actual"]
        st.markdown(f"### 📌 Resumen ({rep['dt_inicio_str']} ➔ {rep['dt_fin_str']})")

        st.write("#### ✍️ Ajuste Manual y Confirmación de Ciclo")
        usuario_activo = st.session_state.get("usuario_activo", {"username": "Victoria", "nombre": "Victoria", "role": "operador"})
        es_admin = usuario_activo.get("role") == "admin"

        if es_admin:
            lista_usrs = [u["username"] for u in auth.listar_usuarios()]
            if usuario_activo["username"] not in lista_usrs:
                lista_usrs.insert(0, usuario_activo["username"])
            idx_def = lista_usrs.index(usuario_activo["username"]) if usuario_activo["username"] in lista_usrs else 0
            usr_registro = st.selectbox("👤 Asignar Ciclo a Operador:", lista_usrs, index=idx_def, key="sel_usr_reg_ciclo")
        else:
            usr_registro = usuario_activo["username"]

        col_aj1, col_aj2, col_aj3 = st.columns([1.5, 2, 1.5])
        with col_aj1:
            ajuste_val = st.number_input("Ajuste USDT (+/-):", value=0.00, step=0.10, format="%.2f")

        ganancia_final_ciclo = rep["profit_base"] + ajuste_val
        pct_ganancia_final = (ganancia_final_ciclo / rep["cap_cic"] * 100) if rep["cap_cic"] > 0 else 0.0

        with col_aj2:
            st.caption(f"Ganancia neta ({usr_registro}):")
            color_badge = "badge-pill-pos" if ganancia_final_ciclo >= 0 else "badge-pill-neg"
            st.markdown(f"""
            <div style="font-size: 1.25rem; font-weight: 700; color: {'#3fb950' if ganancia_final_ciclo >= 0 else '#f85149'};">
                {ganancia_final_ciclo:+,.2f} USDT
                <span class="{color_badge}" style="margin-left: 8px;">{pct_ganancia_final:+.2f}%</span>
            </div>
            """, unsafe_allow_html=True)

        with col_aj3:
            st.write("")
            btn_registrar = st.button("📥 Registrar Ciclo", type="secondary", use_container_width=True)

        if btn_registrar:
            df_h = data_manager.get_historico()
            nuevo_num_ciclo = (int(pd.to_numeric(df_h["Ciclo"], errors="coerce").max()) + 1) if (not df_h.empty and "Ciclo" in df_h.columns and pd.to_numeric(df_h["Ciclo"], errors="coerce").max() > 0) else 1
            com_pct = (rep["com_tot"] / rep["cap_cic"] * 100) if rep["cap_cic"] > 0 else 0.25
            
            nuevo_registro = {
                "Fecha_Hora": rep["fecha_registro"],
                "Ciclo": nuevo_num_ciclo,
                "Comision_Pct": round(com_pct, 3),
                "Tasa_Venta": round(rep["t_vent"], 3),
                "Tasa_Compra": round(rep["t_comp"], 3),
                "Capital": round(rep["cap_cic"], 2),
                "Ganancia_Pct": round(pct_ganancia_final, 2),
                "USDT_Ganado": round(ganancia_final_ciclo, 2),
                "Ajuste": round(ajuste_val, 2),
                "Usuario": usr_registro,
                "Fecha_Inicio": rep.get("dt_inicio_str", ""),
                "Fecha_Fin": rep.get("dt_fin_str", "")
            }
            data_manager.guardar_ciclo(nuevo_registro)
            st.success(f"✅ Ciclo #{nuevo_num_ciclo} registrado para **{usr_registro}** con {ganancia_final_ciclo:+,.2f} USDT.")
            st.toast(f"Ciclo #{nuevo_num_ciclo} guardado para {usr_registro}")

        st.divider()

        d1, d2, d3 = st.columns(3)
        with d1:
            t_vb = rep.get('t_vent_bruta', rep['t_vent'])
            sub_vent = f"Salida efectiva &bull; Bruta: {t_vb:,.3f} {FIAT_CURRENCY}" if abs(t_vb - rep['t_vent']) > 0.001 else "Salida efectiva por USDT"
            st.markdown(f"""
            <div class="metric-card metric-card-sell">
                <div class="metric-label" style="color: #58a6ff;">Tasa Venta (Efectiva)</div>
                <div class="metric-value" style="color: #f0f6fc;">{rep['t_vent']:,.3f} <span style="font-size: 1rem; color: #8b949e;">{FIAT_CURRENCY}</span></div>
                <div class="metric-sub">{sub_vent}</div>
            </div>
            """, unsafe_allow_html=True)

        with d2:
            st.markdown(f"""
            <div class="metric-card metric-card-buy">
                <div class="metric-label" style="color: #e3b341;">Tasa Compra (Efectiva)</div>
                <div class="metric-value" style="color: #f0f6fc;">{rep['t_comp']:,.3f} <span style="font-size: 1rem; color: #8b949e;">{FIAT_CURRENCY}</span></div>
                <div class="metric-sub">Entrada efectiva con redondeos</div>
            </div>
            """, unsafe_allow_html=True)

        with d3:
            st.markdown(f"""
            <div class="metric-card metric-card-profit">
                <div class="metric-label" style="color: #3fb950;">Ganancia Neta Real</div>
                <div class="metric-value" style="color: #3fb950;">{ganancia_final_ciclo:+,.2f} <span style="font-size: 1rem;">USDT</span></div>
                <div class="metric-sub">{'Ajuste incluido: ' + f'{ajuste_val:+.2f} USDT' if ajuste_val != 0 else 'Profit líquido del ciclo'}</div>
            </div>
            """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Capital Ciclado</div>
                <div class="metric-value">{rep['cap_cic']:,.2f} <span style="font-size: 0.9rem; color: #8b949e;">USDT</span></div>
                <div class="metric-sub">Volumen rotado 100%</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            cls_spread = "badge-pill-pos" if rep['spread'] >= 0 else "badge-pill-neg"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Margen de Spread</div>
                <div class="metric-value">{rep['spread']:+.2f}%</div>
                <span class="{cls_spread}">Margen Real de Giro</span>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Comisiones Binance</div>
                <div class="metric-value">{rep['com_tot']:.3f} <span style="font-size: 0.9rem; color: #8b949e;">USDT</span></div>
                <div class="metric-sub">Deducidas en tasas efectivas</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Gasto en Redondeo</div>
                <div class="metric-value">{rep['g_red_u']:.2f} <span style="font-size: 0.9rem; color: #8b949e;">USDT</span></div>
                <span class="badge-pill-neg">-{rep['g_red_fiat']:,.2f} {FIAT_CURRENCY}</span>
            </div>
            """, unsafe_allow_html=True)