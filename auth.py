import hashlib
import json
import os
from pathlib import Path
import streamlit as st

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

def cerrar_sesion():
    st.session_state["usuario_activo"] = None
    st.session_state["autenticado"] = False
    st.rerun()

def verificar_acceso():
    if st.session_state.get("usuario_activo") and st.session_state.get("autenticado"):
        return True

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
                st.success(f"¡Bienvenido, {user_data['nombre']}!")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos. Verifica e intenta de nuevo.")

        st.markdown("""
            <div class="login-footer-pill">
                <span>🛡️</span>
                <span>Sesión cifrada individual &bull; Registro auditado</span>
            </div>
        """, unsafe_allow_html=True)

    st.stop()
