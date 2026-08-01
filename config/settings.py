# ─────────────────────────────────────────────
#  Visor v5.0 — Configuración general
#  Jasol Group · Ing. Jeisson Alberto Sarmiento
#  Saravena, Arauca, Colombia
# ─────────────────────────────────────────────

import os

VERSION      = "5.1.0"
APP_NAME     = "Visor v5.1 — NOC Command Suite"
ORGANIZATION = "Jasol Group"
AUTOR        = "Ing. Jeisson Alberto Sarmiento"
UBICACION    = "Saravena, Arauca, Colombia"

# ── INFRAESTRUCTURA L3 (Jasol Group) ──────────────────────────────────────

# MikroTik Core (Saravena)
MIKROTIK_HOST = "190.1.X.X"       # ← Reemplaza con IP real del Core
MIKROTIK_USER = "admin"
# Nunca guardes contraseñas en el código ni en el repositorio. Configúrala
# mediante la variable de entorno VISOR_MIKROTIK_PASS cuando sea necesario.
MIKROTIK_PASS = os.getenv("VISOR_MIKROTIK_PASS", "")

# Proxmox VE
PROXMOX_HOST        = "10.0.0.X"  # ← IP real del servidor Proxmox
PROXMOX_USER        = "root@pam"
PROXMOX_PASS        = os.getenv("VISOR_PROXMOX_PASS", "")
PROXMOX_TOKEN_ID    = os.getenv("VISOR_PROXMOX_TOKEN_ID", "root@pam!visor")
PROXMOX_TOKEN_SECRET = os.getenv("VISOR_PROXMOX_TOKEN_SECRET", "")

# ── MONITOREO ─────────────────────────────────────────────────────────────
INTERVALO_MONITOREO  = 60   # segundos entre ciclos de monitoreo continuo
PING_COUNT           = 3
PING_TIMEOUT         = 1

# ── LAN VISION ────────────────────────────────────────────────────────────
LAN_SCAN_WORKERS     = 150  # hilos para ping-sweep (ajustar según hardware)
LAN_PORT_WORKERS     = 30   # hilos para escaneo de puertos
LAN_AUTO_RANGO       = True # auto-detectar rango de red local

# ── RAPTOR EYE v5.0 ───────────────────────────────────────────────────────
RAPTOR_MAX_HOSTS     = 254          # máximo de hosts en threat hunting de red
RAPTOR_GRAB_BANNERS  = True         # fingerprinting de servicios
RAPTOR_TIMEOUT       = 0.8          # timeout por puerto (segundos)

# ── REPORTES ──────────────────────────────────────────────────────────────
GUARDAR_REPORTES  = True
FORMATO_REPORTE   = "txt"          # "txt" | "json"
MAX_REPORTES      = 30

# ── ALERTAS EMAIL ─────────────────────────────────────────────────────────
ALERTAS_EMAIL_ACTIVAS = True

# ── DASHBOARD ─────────────────────────────────────────────────────────────
DASHBOARD_URL   = "https://site.zapia.com/sfxt00vr"
SYNC_INTERVAL   = 300   # segundos

# ── COLORES ───────────────────────────────────────────────────────────────
COLORES_ACTIVOS = True
