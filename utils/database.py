"""
utils/database.py — Gestión de persistencia SQLite para Visor v2.5.
Basado en el esquema de METATRON.
"""

import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "visor_data.db"

def inicializar_db():
    """Crea las tablas necesarias si no existen."""
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cursor = conn.cursor()

        # Tabla de historia (sesiones)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historia (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha DATETIME,
                objetivo TEXT,
                tipo_escaneo TEXT,
                resultado_resumen TEXT
            )
        ''')

        # Tabla de vulnerabilidades encontradas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vulnerabilidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sesion_id INTEGER,
                ip TEXT,
                puerto INTEGER,
                servicio TEXT,
                riesgo TEXT,
                descripcion TEXT,
                FOREIGN KEY (sesion_id) REFERENCES historia(id)
            )
        ''')

def guardar_sesion_seguridad(ip: str, auditoria: dict):
    """Guarda los resultados de una auditoría de seguridad."""
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cursor = conn.cursor()

        # Insertar sesión
        cursor.execute(
            "INSERT INTO historia (fecha, objetivo, tipo_escaneo, resultado_resumen) VALUES (?, ?, ?, ?)",
            (auditoria["fecha"], ip, "Auditoría de Seguridad", f"Riesgo: {auditoria['riesgo_general']} - Abiertos: {auditoria['total_abiertos']}")
        )
        sesion_id = cursor.lastrowid

        # Insertar puertos/vulns
        for p in auditoria["puertos_abiertos"]:
            cursor.execute(
                "INSERT INTO vulnerabilidades (sesion_id, ip, puerto, servicio, riesgo, descripcion) VALUES (?, ?, ?, ?, ?, ?)",
                (sesion_id, ip, p["puerto"], p["servicio"], p["riesgo"], p["descripcion"])
            )

    return sesion_id

def obtener_historial_reciente(limit=10):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, fecha, objetivo, resultado_resumen FROM historia ORDER BY fecha DESC LIMIT ?", (limit,))
        return cursor.fetchall()
