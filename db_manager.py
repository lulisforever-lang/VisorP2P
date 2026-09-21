import os
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

# URLs de conexión (Internal para Render en la misma región, External para local o fuera de Render)
INTERNAL_DB_URL = "postgresql://visor_p2p_db_user:4tP1Ar4Kpm4IZP32qTgA7SDXBJLfXLp4@dpg-daktbjjl550s73aqe4l0-a/visor_p2p_db"
EXTERNAL_DB_URL = "postgresql://visor_p2p_db_user:4tP1Ar4Kpm4IZP32qTgA7SDXBJLfXLp4@dpg-daktbjjl550s73aqe4l0-a.frankfurt-postgres.render.com/visor_p2p_db"

def get_connection():
    urls_to_try = []
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        urls_to_try.append(env_url)
    
    # Intentar según el entorno (Internal si está en Render, External si está fuera)
    if os.getenv("RENDER"):
        urls_to_try.extend([INTERNAL_DB_URL, EXTERNAL_DB_URL])
    else:
        urls_to_try.extend([EXTERNAL_DB_URL, INTERNAL_DB_URL])
        
    for url in urls_to_try:
        try:
            conn = psycopg2.connect(url, connect_timeout=4)
            return conn
        except Exception:
            continue
    return None

def is_connected() -> bool:
    conn = get_connection()
    if conn:
        try:
            conn.close()
            return True
        except Exception:
            pass
    return False

def init_db():
    conn = get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            # 1. Tabla historico_ciclos
            cur.execute("""
                CREATE TABLE IF NOT EXISTS historico_ciclos (
                    id SERIAL PRIMARY KEY,
                    "Fecha_Hora" TEXT,
                    "Ciclo" INTEGER,
                    "Comision_Pct" DOUBLE PRECISION,
                    "Tasa_Venta" DOUBLE PRECISION,
                    "Tasa_Compra" DOUBLE PRECISION,
                    "Capital" DOUBLE PRECISION,
                    "Ganancia_Pct" DOUBLE PRECISION,
                    "USDT_Ganado" DOUBLE PRECISION,
                    "Ajuste" DOUBLE PRECISION,
                    "Retiro_Admin" DOUBLE PRECISION DEFAULT 0.0,
                    "Usuario" TEXT,
                    "Fecha_Inicio" TEXT,
                    "Fecha_Fin" TEXT,
                    "Observacion" TEXT DEFAULT ''
                );
            """)

            # 2. Tabla operaciones_manuales
            cur.execute("""
                CREATE TABLE IF NOT EXISTS operaciones_manuales (
                    id TEXT PRIMARY KEY,
                    "Fecha_Hora" TEXT,
                    "tradeType" TEXT,
                    "amount" DOUBLE PRECISION,
                    "unitPrice" DOUBLE PRECISION,
                    "totalPrice" DOUBLE PRECISION,
                    "commission" DOUBLE PRECISION,
                    "fiat" TEXT,
                    "nota" TEXT,
                    "orderStatus" TEXT,
                    "Usuario" TEXT
                );
            """)

            # 3. Tabla usuarios
            cur.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    username TEXT PRIMARY KEY,
                    nombre TEXT,
                    role TEXT,
                    hash TEXT,
                    salt TEXT
                );
            """)
            conn.commit()

            # Migraciones de columnas adicionales en historico_ciclos
            cur.execute("""
                ALTER TABLE historico_ciclos ADD COLUMN IF NOT EXISTS "Fecha_Inicio" TEXT;
                ALTER TABLE historico_ciclos ADD COLUMN IF NOT EXISTS "Fecha_Fin" TEXT;
                ALTER TABLE historico_ciclos ADD COLUMN IF NOT EXISTS "Retiro_Admin" DOUBLE PRECISION DEFAULT 0.0;
                ALTER TABLE historico_ciclos ADD COLUMN IF NOT EXISTS "Observacion" TEXT DEFAULT '';
            """)
            conn.commit()

            # Sembrar ciclos si la tabla está vacía
            cur.execute('SELECT COUNT(*) FROM historico_ciclos;')
            if cur.fetchone()[0] == 0:
                csv_file = BASE_DIR / "historico_ciclos.csv"
                if csv_file.exists():
                    df = pd.read_csv(csv_file)
                    for _, r in df.iterrows():
                        cur.execute("""
                            INSERT INTO historico_ciclos ("Fecha_Hora", "Ciclo", "Comision_Pct", "Tasa_Venta", "Tasa_Compra", "Capital", "Ganancia_Pct", "USDT_Ganado", "Ajuste", "Usuario")
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        """, (
                            str(r.get("Fecha_Hora", "")),
                            int(r.get("Ciclo", 0)),
                            float(r.get("Comision_Pct", 0.0)),
                            float(r.get("Tasa_Venta", 0.0)),
                            float(r.get("Tasa_Compra", 0.0)),
                            float(r.get("Capital", 0.0)),
                            float(r.get("Ganancia_Pct", 0.0)),
                            float(r.get("USDT_Ganado", 0.0)),
                            float(r.get("Ajuste", 0.0)),
                            str(r.get("Usuario", "Victoria"))
                        ))
                    conn.commit()

            # Sembrar operaciones manuales si la tabla está vacía
            cur.execute('SELECT COUNT(*) FROM operaciones_manuales;')
            if cur.fetchone()[0] == 0:
                csv_file = BASE_DIR / "operaciones_manuales.csv"
                if csv_file.exists():
                    df = pd.read_csv(csv_file)
                    for _, r in df.iterrows():
                        cur.execute("""
                            INSERT INTO operaciones_manuales (id, "Fecha_Hora", "tradeType", "amount", "unitPrice", "totalPrice", "commission", "fiat", "nota", "orderStatus", "Usuario")
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING;
                        """, (
                            str(r.get("id")),
                            str(r.get("Fecha_Hora", "")),
                            str(r.get("tradeType", "SELL")),
                            float(r.get("amount", 0.0)),
                            float(r.get("unitPrice", 0.0)),
                            float(r.get("totalPrice", 0.0)),
                            float(r.get("commission", 0.0)),
                            str(r.get("fiat", "VES")),
                            str(r.get("nota", "")) if pd.notna(r.get("nota")) else "",
                            str(r.get("orderStatus", "COMPLETED")),
                            str(r.get("Usuario", "Victoria"))
                        ))
                    conn.commit()

            # Sembrar usuarios si la tabla está vacía
            cur.execute('SELECT COUNT(*) FROM usuarios;')
            if cur.fetchone()[0] == 0:
                usr_file = BASE_DIR / "usuarios.json"
                if usr_file.exists():
                    with open(usr_file, "r", encoding="utf-8") as f:
                        usrs = json.load(f)
                    for k, u in usrs.items():
                        cur.execute("""
                            INSERT INTO usuarios (username, nombre, role, hash, salt)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (username) DO NOTHING;
                        """, (
                            u.get("username", k),
                            u.get("nombre", k),
                            u.get("role", "operador"),
                            u.get("hash", ""),
                            u.get("salt", "")
                        ))
                    conn.commit()

            # Ajuste de consistencia matemática para el Ciclo 10 (deducción correcta de comisión maker de venta)
            cur.execute("""
                UPDATE historico_ciclos
                SET "Tasa_Venta" = 958.799, "USDT_Ganado" = 8.01, "Ganancia_Pct" = 0.05, "Comision_Pct" = 0.125
                WHERE "Ciclo" = 10 AND "USDT_Ganado" = 23.45;
            """)
            conn.commit()

            # Ajuste de consistencia para el Ciclo 7 (Capital arbitrado exacto 19,800 USDT)
            cur.execute("""
                UPDATE historico_ciclos
                SET "Capital" = 19800.0, "Ganancia_Pct" = 0.07
                WHERE "Ciclo" = 7 AND "Capital" > 19800.0;
            """)
            conn.commit()

            # Backfill Fecha_Inicio y Fecha_Fin para ciclos históricos preexistentes
            cur.execute("""
                UPDATE historico_ciclos SET "Fecha_Inicio" = '14/09/2026 07:00 AM', "Fecha_Fin" = '14/09/2026 09:30 AM' WHERE "Ciclo" = 1 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
                UPDATE historico_ciclos SET "Fecha_Inicio" = '14/09/2026 09:30 AM', "Fecha_Fin" = '14/09/2026 01:20 PM' WHERE "Ciclo" = 2 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
                UPDATE historico_ciclos SET "Fecha_Inicio" = '14/09/2026 01:20 PM', "Fecha_Fin" = '14/09/2026 03:30 PM' WHERE "Ciclo" = 3 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
                UPDATE historico_ciclos SET "Fecha_Inicio" = '15/09/2026 02:00 PM', "Fecha_Fin" = '15/09/2026 07:20 PM' WHERE "Ciclo" = 4 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
                UPDATE historico_ciclos SET "Fecha_Inicio" = '15/09/2026 07:00 AM', "Fecha_Fin" = '15/09/2026 09:20 AM' WHERE "Ciclo" = 5 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
                UPDATE historico_ciclos SET "Fecha_Inicio" = '16/09/2026 06:00 AM', "Fecha_Fin" = '16/09/2026 07:45 AM' WHERE "Ciclo" = 6 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
                UPDATE historico_ciclos SET "Fecha_Inicio" = '16/09/2026 07:45 AM', "Fecha_Fin" = '16/09/2026 10:30 AM' WHERE "Ciclo" = 7 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
                UPDATE historico_ciclos SET "Fecha_Inicio" = '16/09/2026 10:30 AM', "Fecha_Fin" = '16/09/2026 12:20 PM' WHERE "Ciclo" = 8 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
                UPDATE historico_ciclos SET "Fecha_Inicio" = '16/09/2026 12:20 PM', "Fecha_Fin" = '16/09/2026 02:00 PM' WHERE "Ciclo" = 9 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
                UPDATE historico_ciclos SET "Fecha_Inicio" = '16/09/2026 01:00 PM', "Fecha_Fin" = '16/09/2026 06:20 PM' WHERE "Ciclo" = 10 AND ("Fecha_Inicio" IS NULL OR "Fecha_Inicio" = '');
            """)
            conn.commit()

        return True
    except Exception as e:
        print(f"Error inicializando base de datos: {e}")
        return False
    finally:
        conn.close()

def db_get_historico():
    conn = get_connection()
    if conn is None:
        return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT "Fecha_Hora", "Ciclo", "Comision_Pct", "Tasa_Venta", "Tasa_Compra", "Capital", "Ganancia_Pct", "USDT_Ganado", "Ajuste", "Retiro_Admin", "Usuario", "Fecha_Inicio", "Fecha_Fin", "Observacion" FROM historico_ciclos ORDER BY "Ciclo" ASC;')
            rows = cur.fetchall()
            return pd.DataFrame(rows)
    except Exception as e:
        print(f"Error leyendo historico_ciclos de DB: {e}")
        return None
    finally:
        conn.close()

def db_guardar_ciclo(reg: dict) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO historico_ciclos ("Fecha_Hora", "Ciclo", "Comision_Pct", "Tasa_Venta", "Tasa_Compra", "Capital", "Ganancia_Pct", "USDT_Ganado", "Ajuste", "Retiro_Admin", "Usuario", "Fecha_Inicio", "Fecha_Fin", "Observacion")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                str(reg.get("Fecha_Hora", "")),
                int(reg.get("Ciclo", 0)),
                float(reg.get("Comision_Pct", 0.0)),
                float(reg.get("Tasa_Venta", 0.0)),
                float(reg.get("Tasa_Compra", 0.0)),
                float(reg.get("Capital", 0.0)),
                float(reg.get("Ganancia_Pct", 0.0)),
                float(reg.get("USDT_Ganado", 0.0)),
                float(reg.get("Ajuste", 0.0)),
                float(reg.get("Retiro_Admin", 0.0)),
                str(reg.get("Usuario", "Victoria")),
                str(reg.get("Fecha_Inicio", "")) if reg.get("Fecha_Inicio") else "",
                str(reg.get("Fecha_Fin", "")) if reg.get("Fecha_Fin") else "",
                str(reg.get("Observacion", "")).strip() if reg.get("Observacion") else ""
            ))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error guardando ciclo en DB: {e}")
        return False
    finally:
        conn.close()

def db_actualizar_ajuste_ciclo(ciclo_num: int, nuevo_ajuste: float, nuevo_usdt: float, nuevo_pct: float) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE historico_ciclos
                SET "Ajuste" = %s, "USDT_Ganado" = %s, "Ganancia_Pct" = %s
                WHERE "Ciclo" = %s;
            """, (float(nuevo_ajuste), float(nuevo_usdt), float(nuevo_pct), int(ciclo_num)))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error actualizando ajuste ciclo en DB: {e}")
        return False
    finally:
        conn.close()

def db_actualizar_ciclo_datos(ciclo_num: int, datos: dict) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        set_clauses = []
        vals = []
        for k, v in datos.items():
            set_clauses.append(f'"{k}" = %s')
            vals.append(v)
        vals.append(int(ciclo_num))
        query = f'UPDATE historico_ciclos SET {", ".join(set_clauses)} WHERE "Ciclo" = %s;'
        with conn.cursor() as cur:
            cur.execute(query, tuple(vals))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error actualizando ciclo en DB: {e}")
        return False
    finally:
        conn.close()

def db_eliminar_ciclo(ciclo_num: int) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM historico_ciclos WHERE "Ciclo" = %s;', (int(ciclo_num),))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error eliminando ciclo en DB: {e}")
        return False
    finally:
        conn.close()

def db_get_operaciones_manuales():
    conn = get_connection()
    if conn is None:
        return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT id, "Fecha_Hora", "tradeType", "amount", "unitPrice", "totalPrice", "commission", "fiat", "nota", "orderStatus", "Usuario" FROM operaciones_manuales ORDER BY "Fecha_Hora" DESC;')
            rows = cur.fetchall()
            return pd.DataFrame(rows)
    except Exception as e:
        print(f"Error leyendo operaciones_manuales de DB: {e}")
        return None
    finally:
        conn.close()

def db_guardar_operacion_manual(reg: dict) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO operaciones_manuales (id, "Fecha_Hora", "tradeType", "amount", "unitPrice", "totalPrice", "commission", "fiat", "nota", "orderStatus", "Usuario")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    "Fecha_Hora" = EXCLUDED."Fecha_Hora",
                    "tradeType" = EXCLUDED."tradeType",
                    "amount" = EXCLUDED."amount",
                    "unitPrice" = EXCLUDED."unitPrice",
                    "totalPrice" = EXCLUDED."totalPrice",
                    "commission" = EXCLUDED."commission",
                    "fiat" = EXCLUDED."fiat",
                    "nota" = EXCLUDED."nota",
                    "orderStatus" = EXCLUDED."orderStatus",
                    "Usuario" = EXCLUDED."Usuario";
            """, (
                str(reg.get("id")),
                str(reg.get("Fecha_Hora", "")),
                str(reg.get("tradeType", "SELL")),
                float(reg.get("amount", 0.0)),
                float(reg.get("unitPrice", 0.0)),
                float(reg.get("totalPrice", 0.0)),
                float(reg.get("commission", 0.0)),
                str(reg.get("fiat", "VES")),
                str(reg.get("nota", "")),
                str(reg.get("orderStatus", "COMPLETED")),
                str(reg.get("Usuario", "Victoria"))
            ))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error guardando operacion manual en DB: {e}")
        return False
    finally:
        conn.close()

def db_actualizar_operacion_manual(op_id: str, datos: dict) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        set_clauses = []
        vals = []
        for k, v in datos.items():
            set_clauses.append(f'"{k}" = %s')
            vals.append(v)
        vals.append(str(op_id))
        query = f'UPDATE operaciones_manuales SET {", ".join(set_clauses)} WHERE id = %s;'
        with conn.cursor() as cur:
            cur.execute(query, tuple(vals))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error actualizando operacion manual en DB: {e}")
        return False
    finally:
        conn.close()

def db_eliminar_operacion_manual(op_id: str) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM operaciones_manuales WHERE id = %s;', (str(op_id),))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error eliminando operacion manual en DB: {e}")
        return False
    finally:
        conn.close()

def db_get_usuarios() -> dict | None:
    conn = get_connection()
    if conn is None:
        return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT username, nombre, role, hash, salt FROM usuarios;')
            rows = cur.fetchall()
            result = {}
            for r in rows:
                key = str(r["username"]).strip().lower()
                result[key] = dict(r)
            return result
    except Exception as e:
        print(f"Error obteniendo usuarios de DB: {e}")
        return None
    finally:
        conn.close()

def db_guardar_usuario(username: str, data: dict) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO usuarios (username, nombre, role, hash, salt)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (username) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    role = EXCLUDED.role,
                    hash = EXCLUDED.hash,
                    salt = EXCLUDED.salt;
            """, (
                data.get("username", username),
                data.get("nombre", username),
                data.get("role", "operador"),
                data.get("hash", ""),
                data.get("salt", "")
            ))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error guardando usuario en DB: {e}")
        return False
    finally:
        conn.close()

def db_eliminar_usuario(username: str) -> bool:
    conn = get_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM usuarios WHERE LOWER(username) = LOWER(%s);', (str(username),))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error eliminando usuario de DB: {e}")
        return False
    finally:
        conn.close()
