"""
config.py
=========
Configuración centralizada de la API.
Cambia aquí la IP del ESP32 y las credenciales de MySQL.
"""

# ── ESP32 ──────────────────────────────────────────────────
# IP que aparece en el Monitor Serie de Arduino IDE al arrancar el ESP32
ESP32_IP       = "192.168.X.X"          
ESP32_BASE_URL = f"http://{ESP32_IP}"

# ── Recolección automática ─────────────────────────────────
INTERVALO_SEG = 2   # Cada cuántos segundos se consulta el ESP32

# ── MySQL ──────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "port":     3307,
    "password": "goberment31",      
    "database": "seguridad_hogar",
}
