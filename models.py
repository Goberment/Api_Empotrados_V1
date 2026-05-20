"""
models.py
=========
Modelos Pydantic para validación de entrada y serialización de salida.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── ESP32 ──────────────────────────────────────────────────

class SensoresESP32(BaseModel):
    distancia_cm:  float
    vibracion_g:   float
    temperatura_c: float
    humedad_pct:   float


class ActuadoresESP32(BaseModel):
    buzzer:        bool
    led:           bool
    servo_cerrado: bool


class EstadoESP32(BaseModel):
    estado:     str
    sensores:   SensoresESP32
    actuadores: ActuadoresESP32


class ParametrosESP32(BaseModel):
    distancia_minima_cm: float
    umbral_vibracion_g:  float


# ── Entrada ────────────────────────────────────────────────

class ParametrosUpdate(BaseModel):
    distancia_minima_cm: Optional[float] = Field(
        None, gt=0, le=400,
        description="Distancia mínima en cm antes de activar la alarma"
    )
    umbral_vibracion_g: Optional[float] = Field(
        None, gt=0, le=20,
        description="Magnitud de vibración en g para activar la alarma"
    )


# ── MySQL / Histórico ──────────────────────────────────────

class LecturaDB(BaseModel):
    id:            int
    fecha_hora:    datetime
    distancia_cm:  float
    vibracion_g:   float
    temperatura_c: float
    humedad_pct:   float
    estado:        str

    model_config = {"from_attributes": True}


class AlertaDB(BaseModel):
    id:          int
    lectura_id:  int
    fecha_hora:  datetime
    tipo:        str
    descripcion: str
    resuelta:    bool

    model_config = {"from_attributes": True}


class ActuadorLogDB(BaseModel):
    id:         int
    lectura_id: int
    fecha_hora: datetime
    actuador:   str
    accion:     str

    model_config = {"from_attributes": True}


# ── Estadísticas ───────────────────────────────────────────

class ResumenEstadistico(BaseModel):
    horas:            int
    total_lecturas:   int
    dist_min:         Optional[float]
    dist_max:         Optional[float]
    dist_avg:         Optional[float]
    vib_min:          Optional[float]
    vib_max:          Optional[float]
    vib_avg:          Optional[float]
    temp_min:         Optional[float]
    temp_max:         Optional[float]
    temp_avg:         Optional[float]
    hum_min:          Optional[float]
    hum_max:          Optional[float]
    hum_avg:          Optional[float]
    total_alertas:    int
    total_bloqueados: int
