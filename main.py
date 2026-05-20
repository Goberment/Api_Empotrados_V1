"""
main.py
=======
API REST - Sistema de Seguridad ESP32
--------------------------------------
Servidor FastAPI que actúa como capa intermedia entre el ESP32,
la base de datos MySQL y cualquier cliente (GUI, web, móvil).

Funciones:
  - Proxy hacia el ESP32 (reenvía comandos, lee estado en vivo)
  - Recolección automática en background (reemplaza recolector.py)
  - Consulta de histórico desde MySQL
  - Documentación interactiva en /docs

Autores: [Diego Montes, Gabriela Soto]
"""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import asyncio
import httpx

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import ESP32_BASE_URL, INTERVALO_SEG
from database import get_db_connection, close_connection
from models import (
    ParametrosUpdate,
    LecturaDB,
    AlertaDB,
    ActuadorLogDB,
    EstadoESP32,
    ParametrosESP32,
    ResumenEstadistico,
)
from recolector import ciclo_recoleccion


# ─────────────────────────────────────────────
# Lifespan: inicia / detiene el recolector
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicia la tarea de recolección al arrancar y la cancela al apagar."""
    task = asyncio.create_task(ciclo_recoleccion())
    print(f"[RECOLECTOR] Iniciado — consultando ESP32 cada {INTERVALO_SEG}s")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    print("[RECOLECTOR] Detenido.")


# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────

app = FastAPI(
    title="API Sistema de Seguridad ESP32",
    description=(
        "API REST que integra el ESP32 con MySQL. "
        "Recolecta datos de sensores, registra alertas y expone "
        "endpoints para consulta y control del sistema."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# PROXY → ESP32  (estado en vivo y comandos)
# ═══════════════════════════════════════════════════════════

@app.get(
    "/esp32/estado",
    response_model=EstadoESP32,
    tags=["ESP32 — en vivo"],
    summary="Estado en tiempo real del ESP32",
)
async def get_estado_esp32():
    """
    Consulta el ESP32 directamente y devuelve el estado actual
    de sensores y actuadores **en tiempo real** (sin pasar por MySQL).
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{ESP32_BASE_URL}/api/estado")
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        raise HTTPException(503, "No se puede conectar al ESP32")
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout al consultar el ESP32")


@app.get(
    "/esp32/parametros",
    response_model=ParametrosESP32,
    tags=["ESP32 — en vivo"],
    summary="Parámetros actuales del ESP32",
)
async def get_parametros_esp32():
    """Devuelve los umbrales configurados actualmente en el ESP32."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{ESP32_BASE_URL}/api/parametros")
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        raise HTTPException(503, "No se puede conectar al ESP32")
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout al consultar el ESP32")


@app.post(
    "/esp32/parametros",
    response_model=ParametrosESP32,
    tags=["ESP32 — en vivo"],
    summary="Actualiza umbrales en el ESP32",
)
async def post_parametros_esp32(body: ParametrosUpdate):
    """
    Envía nuevos umbrales al ESP32 y los persiste en MySQL
    (tabla `parametro`).

    Solo se actualizan los campos incluidos en el body.
    """
    payload = body.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(400, "Debes enviar al menos un parámetro")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(
                f"{ESP32_BASE_URL}/api/parametros",
                json=payload,
            )
        r.raise_for_status()
        result = r.json()
    except httpx.ConnectError:
        raise HTTPException(503, "No se puede conectar al ESP32")
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout al consultar el ESP32")

    # Persistir en MySQL
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for nombre, valor in payload.items():
            cursor.execute(
                """
                UPDATE parametro
                SET valor = %s, actualizado_en = NOW()
                WHERE nombre = %s
                """,
                (valor, nombre),
            )
        conn.commit()
        cursor.close()
    finally:
        close_connection(conn)

    return result


@app.post(
    "/esp32/reset",
    tags=["ESP32 — en vivo"],
    summary="Desbloquea el sistema de alarma",
)
async def post_reset_esp32():
    """
    Envía el comando de reset al ESP32.
    Desactiva buzzer, LED y servo; regresa al estado IDLE.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(f"{ESP32_BASE_URL}/api/reset")
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        raise HTTPException(503, "No se puede conectar al ESP32")
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout al consultar el ESP32")


# ═══════════════════════════════════════════════════════════
# HISTÓRICO — Lecturas
# ═══════════════════════════════════════════════════════════

@app.get(
    "/lecturas",
    response_model=list[LecturaDB],
    tags=["Histórico"],
    summary="Listado de lecturas de sensores",
)
def get_lecturas(
    horas: int = Query(1, ge=1, le=720, description="Últimas N horas"),
    limit: int = Query(500, ge=1, le=5000, description="Máximo de registros"),
):
    """
    Devuelve las lecturas de sensores almacenadas en MySQL
    dentro de las últimas **horas** indicadas.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        desde = datetime.now() - timedelta(hours=horas)
        cursor.execute(
            """
            SELECT * FROM lectura
            WHERE fecha_hora >= %s
            ORDER BY fecha_hora DESC
            LIMIT %s
            """,
            (desde, limit),
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        close_connection(conn)


@app.get(
    "/lecturas/ultima",
    response_model=LecturaDB,
    tags=["Histórico"],
    summary="Última lectura registrada",
)
def get_ultima_lectura():
    """Devuelve la lectura más reciente en MySQL."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM lectura ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        if not row:
            raise HTTPException(404, "No hay lecturas registradas aún")
        return row
    finally:
        close_connection(conn)


@app.get(
    "/lecturas/resumen",
    response_model=ResumenEstadistico,
    tags=["Histórico"],
    summary="Estadísticas resumidas del período",
)
def get_resumen(
    horas: int = Query(24, ge=1, le=720, description="Últimas N horas"),
):
    """
    Calcula mínimos, máximos y promedios de cada sensor
    para el período indicado.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        desde = datetime.now() - timedelta(hours=horas)
        cursor.execute(
            """
            SELECT
                COUNT(*)           AS total_lecturas,
                MIN(distancia_cm)  AS dist_min,
                MAX(distancia_cm)  AS dist_max,
                AVG(distancia_cm)  AS dist_avg,
                MIN(vibracion_g)   AS vib_min,
                MAX(vibracion_g)   AS vib_max,
                AVG(vibracion_g)   AS vib_avg,
                MIN(temperatura_c) AS temp_min,
                MAX(temperatura_c) AS temp_max,
                AVG(temperatura_c) AS temp_avg,
                MIN(humedad_pct)   AS hum_min,
                MAX(humedad_pct)   AS hum_max,
                AVG(humedad_pct)   AS hum_avg,
                SUM(estado = 'ALERTA')    AS total_alertas,
                SUM(estado = 'BLOQUEADO') AS total_bloqueados
            FROM lectura
            WHERE fecha_hora >= %s
            """,
            (desde,),
        )
        row = cursor.fetchone()
        cursor.close()
        return {**row, "horas": horas}
    finally:
        close_connection(conn)


# ═══════════════════════════════════════════════════════════
# HISTÓRICO — Alertas
# ═══════════════════════════════════════════════════════════

@app.get(
    "/alertas",
    response_model=list[AlertaDB],
    tags=["Histórico"],
    summary="Historial de alertas",
)
def get_alertas(
    limit: int = Query(50, ge=1, le=500),
    solo_no_resueltas: bool = Query(False, description="Filtrar solo alertas pendientes"),
):
    """Devuelve el historial de alertas registradas."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        where = "WHERE resuelta = FALSE" if solo_no_resueltas else ""
        cursor.execute(
            f"SELECT * FROM alerta {where} ORDER BY fecha_hora DESC LIMIT %s",
            (limit,),
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        close_connection(conn)


@app.patch(
    "/alertas/{alerta_id}/resolver",
    tags=["Histórico"],
    summary="Marca una alerta como resuelta",
)
def resolver_alerta(alerta_id: int):
    """Actualiza el campo `resuelta = TRUE` de la alerta indicada."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE alerta SET resuelta = TRUE WHERE id = %s",
            (alerta_id,),
        )
        if cursor.rowcount == 0:
            raise HTTPException(404, f"Alerta {alerta_id} no encontrada")
        conn.commit()
        cursor.close()
        return {"ok": True, "alerta_id": alerta_id, "resuelta": True}
    finally:
        close_connection(conn)


# ═══════════════════════════════════════════════════════════
# HISTÓRICO — Actuadores
# ═══════════════════════════════════════════════════════════

@app.get(
    "/actuadores/log",
    response_model=list[ActuadorLogDB],
    tags=["Histórico"],
    summary="Historial de acciones de actuadores",
)
def get_actuadores_log(
    limit: int = Query(50, ge=1, le=500),
    actuador: str | None = Query(None, description="Filtrar: BUZZER, LED o SERVO"),
):
    """Devuelve el log de acciones ejecutadas por los actuadores."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if actuador:
            cursor.execute(
                "SELECT * FROM actuador_log WHERE actuador = %s ORDER BY fecha_hora DESC LIMIT %s",
                (actuador.upper(), limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM actuador_log ORDER BY fecha_hora DESC LIMIT %s",
                (limit,),
            )
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        close_connection(conn)


# ═══════════════════════════════════════════════════════════
# PARÁMETROS — MySQL
# ═══════════════════════════════════════════════════════════

@app.get(
    "/parametros",
    tags=["Parámetros"],
    summary="Parámetros guardados en MySQL",
)
def get_parametros_db():
    """Lee los parámetros de la tabla `parametro` en MySQL."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM parametro ORDER BY nombre")
        rows = cursor.fetchall()
        cursor.close()
        return rows
    finally:
        close_connection(conn)
