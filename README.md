# API REST — Sistema de Seguridad ESP32

API construida con **FastAPI** que integra el ESP32, MySQL y cualquier cliente
(GUI de Python, web, móvil).  
Incluye recolección automática de datos en background: **ya no necesitas
correr `recolector.py` en una terminal aparte**.

---

## Estructura del proyecto

```
api_seguridad/
├── main.py          ← App FastAPI + todos los endpoints
├── recolector.py    ← Tarea en background (reemplaza al recolector original)
├── database.py      ← Helpers de conexión MySQL
├── models.py        ← Esquemas Pydantic (validación y documentación)
├── config.py        ← ⚙️  IP del ESP32 y credenciales MySQL
└── requirements.txt
```

---

## ⚙️ Configuración (`config.py`)

```python
ESP32_IP       = "192.168.X.X"   # IP del ESP32 (Monitor Serie)
INTERVALO_SEG  = 2               # Segundos entre consultas al ESP32

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "TU_CONTRASEÑA", # Contraseña MySQL
    "database": "seguridad_hogar",
}
```

---

## 🚀 Instalación y ejecución

```bash
# 1 — Instalar dependencias
pip install -r requirements.txt

# 2 — Editar config.py con tu IP y contraseña

# 3 — Ejecutar
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

La API queda en `http://localhost:8000`  
Documentación interactiva (Swagger): `http://localhost:8000/docs`

---

## Endpoints

### ESP32 — tiempo real

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET`  | `/esp32/estado` | Estado actual de sensores y actuadores |
| `GET`  | `/esp32/parametros` | Umbrales configurados en el ESP32 |
| `POST` | `/esp32/parametros` | Actualiza umbrales (y los guarda en MySQL) |
| `POST` | `/esp32/reset` | Desbloquea la alarma |

**Ejemplo — actualizar umbral:**
```bash
curl -X POST http://localhost:8000/esp32/parametros \
     -H "Content-Type: application/json" \
     -d '{"distancia_minima_cm": 30.0}'
```

---

### Histórico — MySQL

| Método  | Ruta | Descripción |
|---------|------|-------------|
| `GET`   | `/lecturas?horas=1` | Lecturas de los últimas N horas |
| `GET`   | `/lecturas/ultima` | Lectura más reciente |
| `GET`   | `/lecturas/resumen?horas=24` | Estadísticas: min/max/avg de sensores |
| `GET`   | `/alertas` | Historial de alertas |
| `GET`   | `/alertas?solo_no_resueltas=true` | Solo alertas pendientes |
| `PATCH` | `/alertas/{id}/resolver` | Marca alerta como resuelta |
| `GET`   | `/actuadores/log` | Log de actuadores |
| `GET`   | `/actuadores/log?actuador=SERVO` | Filtrado por actuador |
| `GET`   | `/parametros` | Parámetros guardados en MySQL |

---

## Actualizar `gui.py` para usar la API

Si quieres que la GUI use esta API en lugar de conectarse directamente
al ESP32, reemplaza las llamadas en `gui.py`:

```python
# Antes (directo al ESP32):
BASE_URL = f"http://{ESP32_IP}"
r = requests.get(f"{BASE_URL}/api/estado")

# Ahora (a través de la API REST):
API_URL = "http://localhost:8000"
r = requests.get(f"{API_URL}/esp32/estado")

# Lecturas históricas desde MySQL (antes usaba mysql.connector directamente):
r = requests.get(f"{API_URL}/lecturas?horas=1")
lecturas = r.json()
```

Esto hace que la GUI no necesite credenciales MySQL ni acceso directo al ESP32.

---

## Orden de ejecución completo

```
1. Cargar main.ino al ESP32
2. Anotar la IP del Monitor Serie → poner en config.py
3. Ejecutar: uvicorn main:app --host 0.0.0.0 --port 8000
4. (Opcional) Ejecutar gui.py apuntando a http://localhost:8000
```

Ya **no** necesitas correr `recolector.py` por separado.
