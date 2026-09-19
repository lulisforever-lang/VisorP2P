import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).resolve().parent
USUARIOS_FILE = BASE_DIR / "usuarios.json"

def cargar_css(ruta_relativa):
    ruta = BASE_DIR / ruta_relativa
    if ruta.exists():
        with open(ruta, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def hash_pw(pw: str, salt: str = None) -> tuple[str, str]:
    if not salt:
        salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt), 100000).hex()
    return h, salt

def check_pw(pw: str, stored_hash: str, stored_salt: str) -> bool:
    calc_hash, _ = hash_pw(pw, stored_salt)
    return calc_hash == stored_hash

def get_usuarios_dict() -> dict:
    # 1. Intentar PostgreSQL (db_manager)
    try:
        import db_manager
        users_db = db_manager.db_get_usuarios()
        if users_db:
            return users_db
    except Exception:
        pass

    # 2. Archivo local JSON
    if not USUARIOS_FILE.exists():
        # Inicialización de usuarios por defecto
        admin_h, admin_s = hash_pw("Metr!cas502*.")
        vic_h, vic_s = hash_pw("Victor123")
        init_data = {
            "luisit0jr": {
                "username": "Luisit0Jr",
                "nombre": "Luisito Jr",
                "role": "admin",
                "hash": admin_h,
                "salt": admin_s
            },
            "victoria": {
                "username": "Victoria",
                "nombre": "Victoria",
                "role": "operador",
                "hash": vic_h,
                "salt": vic_s
            }
        }
        guardar_usuarios_dict(init_data)
        return init_data

    try:
        with open(USUARIOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def guardar_usuarios_dict(data: dict) -> bool:
    # 1. Guardar en PostgreSQL (db_manager)
    try:
        import db_manager
        for k, u in data.items():
            db_manager.db_guardar_usuario(k, u)
    except Exception:
        pass

    # 2. Guardar copia local JSON
    try:
        with open(USUARIOS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error guardando usuarios: {e}")
        return False

def autenticar(username: str, password: str) -> dict | None:
    if not username or not password:
        return None
    users = get_usuarios_dict()
    key = username.strip().lower()
    if key not in users:
        return None
    user_info = users[key]
    pw = password.strip()
    hash_val = user_info.get("hash", "")
    salt_val = user_info.get("salt", "")
    if check_pw(pw, hash_val, salt_val) or \
       (pw.endswith(".") and check_pw(pw[:-1], hash_val, salt_val)) or \
       check_pw(pw + ".", hash_val, salt_val):
        return {
            "username": user_info.get("username", username),
            "nombre": user_info.get("nombre", username),
            "role": user_info.get("role", "operador")
        }
    return None

def crear_usuario(username: str, password: str, nombre: str, role: str = "operador") -> tuple[bool, str]:
    if not username or not password:
        return False, "Usuario y contraseña requeridos."
    key = username.strip().lower()
    users = get_usuarios_dict()
    if key in users:
        return False, f"El usuario '{username}' ya existe."
    h, s = hash_pw(password.strip())
    users[key] = {
        "username": username.strip(),
        "nombre": nombre.strip() if nombre else username.strip(),
        "role": role if role in ["admin", "operador"] else "operador",
        "hash": h,
        "salt": s
    }
    if guardar_usuarios_dict(users):
        return True, f"Usuario '{username}' creado exitosamente."
    return False, "Error al guardar el nuevo usuario."

def cambiar_password(username: str, new_password: str) -> tuple[bool, str]:
    if not new_password or len(new_password.strip()) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres."
    key = username.strip().lower()
    users = get_usuarios_dict()
    if key not in users:
        return False, f"Usuario '{username}' no encontrado."
    h, s = hash_pw(new_password.strip())
    users[key]["hash"] = h
    users[key]["salt"] = s
    if guardar_usuarios_dict(users):
        return True, f"Contraseña actualizada para '{username}'."
    return False, "Error al actualizar la contraseña."

def eliminar_usuario(username: str) -> tuple[bool, str]:
    key = username.strip().lower()
    users = get_usuarios_dict()
    if key not in users:
        return False, f"Usuario '{username}' no encontrado."
    if users[key].get("role") == "admin":
        return False, "No se puede eliminar la cuenta principal de Administrador."
    
    # 1. Eliminar en PostgreSQL (db_manager)
    try:
        import db_manager
        db_manager.db_eliminar_usuario(key)
    except Exception:
        pass

    del users[key]
    if guardar_usuarios_dict(users):
        return True, f"Usuario '{username}' eliminado correctamente."
    return False, "Error al eliminar usuario."

def listar_usuarios() -> list[dict]:
    users = get_usuarios_dict()
    res = []
    for k, v in users.items():
        res.append({
            "username": v.get("username", k),
            "nombre": v.get("nombre", k),
            "role": v.get("role", "operador")
        })
    return res

SESSION_DURATION_SECONDS = 20 * 60  # 20 minutos de inactividad
SESSION_RENEW_THRESHOLD = 10 * 60   # Renovar si quedan menos de 10 minutos
SECRET_FILE = BASE_DIR / ".session_secret"

def _get_secret_key() -> str:
    sec = os.getenv("SESSION_SECRET")
    if sec:
        return sec
    if SECRET_FILE.exists():
        try:
            with open(SECRET_FILE, "r", encoding="utf-8") as f:
                s = f.read().strip()
                if s:
                    return s
        except Exception:
            pass
    nuevo_sec = os.urandom(32).hex()
    try:
        with open(SECRET_FILE, "w", encoding="utf-8") as f:
            f.write(nuevo_sec)
    except Exception:
        pass
    return nuevo_sec

def generar_token_sesion(user_data: dict, duracion_segundos: int = SESSION_DURATION_SECONDS) -> str:
    now = int(time.time())
    payload = {
        "username": user_data.get("username", ""),
        "nombre": user_data.get("nombre", ""),
        "role": user_data.get("role", "operador"),
        "exp": now + duracion_segundos,
        "iat": now
    }
    raw_payload = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    b64_payload = base64.urlsafe_b64encode(raw_payload).decode('utf-8').rstrip('=')
    secret = _get_secret_key().encode('utf-8')
    sig = hmac.new(secret, b64_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{sig}"

def validar_token_sesion(token: str) -> tuple[dict | None, bool]:
    """
    Retorna (user_data, debe_renovar).
    - user_data: dict si el token es válido y no ha expirado, o None si expiró/inválido.
    - debe_renovar: True si el token es válido pero está en el umbral de renovación.
    """
    if not token or "." not in token:
        return None, False
    try:
        parts = token.strip().split(".")
        if len(parts) != 2:
            return None, False
        b64_payload, sig = parts
        secret = _get_secret_key().encode('utf-8')
        calc_sig = hmac.new(secret, b64_payload.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, calc_sig):
            return None, False

        padded = b64_payload + '=' * (-len(b64_payload) % 4)
        raw_json = base64.urlsafe_b64decode(padded).decode('utf-8')
        payload = json.loads(raw_json)

        now = int(time.time())
        exp = payload.get("exp", 0)
        if now > exp:
            return None, False

        users = get_usuarios_dict()
        key = str(payload.get("username", "")).strip().lower()
        if key not in users:
            return None, False

        user_info = users[key]
        user_data = {
            "username": user_info.get("username", payload.get("username")),
            "nombre": user_info.get("nombre", payload.get("nombre")),
            "role": user_info.get("role", payload.get("role", "operador"))
        }

        debe_renovar = (exp - now) < SESSION_RENEW_THRESHOLD
        return user_data, debe_renovar
    except Exception:
        return None, False

def sincronizar_token_en_browser(token: str):
    components.html(f"""
    <script>
    try {{
        localStorage.setItem("ricomcpato_p2p_session", "{token}");
    }} catch(e) {{}}
    </script>
    """, height=0)

def limpiar_token_en_browser():
    components.html("""
    <script>
    try {
        localStorage.removeItem("ricomcpato_p2p_session");
    } catch(e) {}
    </script>
    """, height=0)

def cerrar_sesion():
    st.session_state["usuario_activo"] = None
    st.session_state["autenticado"] = False
    st.query_params.pop("session", None)
    st.query_params.pop("view", None)
    limpiar_token_en_browser()
    components.html("""
    <script>
    try {
        localStorage.removeItem("ricomcpato_p2p_session");
        const url = new URL(window.location.href);
        url.searchParams.delete("session");
        url.searchParams.delete("view");
        window.location.replace(url.pathname);
    } catch(e) {}
    </script>
    """, height=0)
    st.rerun()

def verificar_acceso():
    # 1. Si ya está autenticado en st.session_state
    if st.session_state.get("usuario_activo") and st.session_state.get("autenticado"):
        token_actual = st.query_params.get("session")
        if token_actual:
            user_data, debe_renovar = validar_token_sesion(token_actual)
            if debe_renovar and user_data:
                nuevo_tok = generar_token_sesion(user_data)
                st.query_params["session"] = nuevo_tok
                sincronizar_token_en_browser(nuevo_tok)
        return True

    # 2. Si no está en session_state (tras refrescar página F5 o reconexión de WebSocket)
    token = st.query_params.get("session")
    if token:
        user_data, debe_renovar = validar_token_sesion(token)
        if user_data:
            st.session_state["usuario_activo"] = user_data
            st.session_state["autenticado"] = True
            if debe_renovar:
                nuevo_tok = generar_token_sesion(user_data)
                st.query_params["session"] = nuevo_tok
                sincronizar_token_en_browser(nuevo_tok)
            return True
        else:
            # Token expirado o inválido: limpiarlo
            st.query_params.pop("session", None)
            limpiar_token_en_browser()
            st.warning("⏱️ Tu sesión ha expirado tras más de 15 minutos de inactividad. Por favor ingresa nuevamente.")

    # 3. Intentar restaurar sesión desde localStorage si el usuario abrió la URL limpia
    components.html("""
    <script>
    (function() {
        try {
            const s = localStorage.getItem("ricomcpato_p2p_session");
            if (s && !window.location.search.includes("session=")) {
                const url = new URL(window.location.href);
                url.searchParams.set("session", s);
                window.location.replace(url.toString());
            }
        } catch(e) {}
    })();
    </script>
    """, height=0)

    cargar_css("auth.css")

    with st.form("form_login", clear_on_submit=False):
        st.markdown("""
            <div class="login-header-box">
                <div class="login-brand-title">
                    <span>🦆</span>
                    <span>RicoMcPato</span>
                </div>
                <div class="login-pill-badge">Visor Financiero P2P</div>
                <div class="login-lock-heading">
                    <span>🔐</span> Iniciar Sesión
                </div>
                <p class="login-subtext">Ingresa tus credenciales para acceder al sistema y registrar tus ciclos.</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<label class="login-input-label">Usuario:</label>', unsafe_allow_html=True)
        user_ingresado = st.text_input(
            "Usuario:",
            placeholder="Tu nombre de usuario",
            max_chars=30,
            label_visibility="collapsed",
            key="login_user_input"
        )

        st.markdown('<label class="login-input-label" style="margin-top: 10px;">Contraseña:</label>', unsafe_allow_html=True)
        pass_ingresado = st.text_input(
            "Contraseña:",
            type="password",
            placeholder="Tu contraseña",
            max_chars=40,
            label_visibility="collapsed",
            key="login_pass_input"
        )

        st.write("")
        btn_entrar = st.form_submit_button("Entrar al Sistema 🚀", type="primary", use_container_width=True)

        if btn_entrar:
            user_data = autenticar(user_ingresado, pass_ingresado)
            if user_data:
                st.session_state["usuario_activo"] = user_data
                st.session_state["autenticado"] = True
                tok = generar_token_sesion(user_data)
                st.query_params["session"] = tok
                sincronizar_token_en_browser(tok)
                st.success(f"¡Bienvenido, {user_data['nombre']}!")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos. Verifica e intenta de nuevo.")

        st.markdown("""
            <div class="login-footer-pill">
                <span>🛡️</span>
                <span>Sesión segura con persistencia &bull; Registro auditado</span>
            </div>
        """, unsafe_allow_html=True)

    st.stop()
