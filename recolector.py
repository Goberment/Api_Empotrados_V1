"""
recolector.py
=============
Tarea asíncrona de recolección de datos.

Reemplaza el recolector.py original (que era un proceso separado).
Aquí corre como background task dentro del mismo proceso FastAPI,
por lo que NO necesitas ejecutar recolector.py en otra terminal.
"""

import asyncio
from datetime import datetime

import httpx

from config import ESP32_BASE_URL, INTERVALO_SEG
from database import get_db_connection, close_connection


# Estado anterior para detectar cambios en actuadores
_estado_anterior = {
    "buzzer":        False,
    "led":           False,
    "servo_cerrado": False,
    "estado":        "NORMAL",
}


def _guardar_lectura(conn, datos: dict) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO lectura
            (fecha_hora, distancia_cm, vibracion_g, temperatura_c, humedad_pct, estado)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            datetime.now(),
            datos["sensores"]["distancia_cm"],
            datos["sensores"]["vibracion_g"],
            datos["sensores"]["temperatura_c"],
            datos["sensores"]["humedad_pct"],
            datos["estado"],
        ),
    )
    conn.commit()
    lectura_id = cursor.lastrowid
    cursor.close()
    return lectura_id


def _guardar_alerta(conn, lectura_id: int, tipo: str, descripcion: str):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO alerta (lectura_id, fecha_hora, tipo, descripcion, resuelta)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (lectura_id, datetime.now(), tipo, descripcion, False),
    )
    conn.commit()
    cursor.close()


def _guardar_actuador(conn, lectura_id: int, actuador: str, accion: str):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO actuador_log (lectura_id, fecha_hora, actuador, accion)
        VALUES (%s, %s, %s, %s)
        """,
        (lectura_id, datetime.now(), actuador, accion),
    )
    conn.commit()
    cursor.close()


def _procesar(conn, datos: dict):
    """Guarda lectura, detecta alertas y cambios de actuadores."""
    global _estado_anterior

    lectura_id = _guardar_lectura(conn, datos)
    print(f"[RECOLECTOR] Lectura #{lectura_id} — {datos['estado']}")

    # Alertas
    if datos["estado"] in ("ALERTA", "BLOQUEADO"):
        if datos["sensores"]["distancia_cm"] < 50:
            _guardar_alerta(
                conn, lectura_id, "DISTANCIA",
                f"Distancia {datos['sensores']['distancia_cm']:.1f} cm bajo umbral",
            )
        if datos["sensores"]["vibracion_g"] > 1.5:
            _guardar_alerta(
                conn, lectura_id, "VIBRACION",
                f"Vibración {datos['sensores']['vibracion_g']:.2f} g sobre umbral",
            )

    # Cambios de actuadores
    act = datos["actuadores"]
    if act["buzzer"] != _estado_anterior["buzzer"]:
        _guardar_actuador(conn, lectura_id, "BUZZER", "ON" if act["buzzer"] else "OFF")
    if act["led"] != _estado_anterior["led"]:
        _guardar_actuador(conn, lectura_id, "LED", "ON" if act["led"] else "OFF")
    if act["servo_cerrado"] != _estado_anterior["servo_cerrado"]:
        _guardar_actuador(conn, lectura_id, "SERVO",
                          "CERRAR" if act["servo_cerrado"] else "ABRIR")

    _estado_anterior.update({
        "buzzer":        act["buzzer"],
        "led":           act["led"],
        "servo_cerrado": act["servo_cerrado"],
        "estado":        datos["estado"],
    })


async def ciclo_recoleccion():
    """
    Corre en background: consulta el ESP32 cada INTERVALO_SEG segundos
    y persiste los datos en MySQL.
    """
    conn = None
    while True:
        try:
            # Conectar a MySQL si es necesario
            if conn is None or not conn.is_connected():
                conn = get_db_connection()
                print("[RECOLECTOR] Conectado a MySQL")

            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{ESP32_BASE_URL}/api/estado")

            if r.status_code == 200:
                _procesar(conn, r.json())
            else:
                print(f"[RECOLECTOR] ESP32 respondió {r.status_code}")

        except httpx.ConnectError:
            print("[RECOLECTOR] No se pudo conectar al ESP32 — reintentando...")
        except httpx.TimeoutException:
            print("[RECOLECTOR] Timeout al consultar el ESP32")
        except Exception as exc:
            print(f"[RECOLECTOR] Error: {exc}")
            close_connection(conn)
            conn = None

        await asyncio.sleep(INTERVALO_SEG)
