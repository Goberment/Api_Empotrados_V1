"""
database.py
===========
Helpers de conexión a MySQL.
"""

import mysql.connector
from config import DB_CONFIG


def get_db_connection():
    """Abre y devuelve una conexión a MySQL."""
    return mysql.connector.connect(**DB_CONFIG)


def close_connection(conn):
    """Cierra la conexión si está abierta."""
    try:
        if conn and conn.is_connected():
            conn.close()
    except Exception:
        pass
