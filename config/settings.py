# ─────────────────────────────────────────────
#  Visor v5.0 — Configuración general
#  Jasol Group · Ing. Jeisson Alberto Sarmiento
#  Saravena, Arauca, Colombia
# ─────────────────────────────────────────────

VERSION      = "5.0.0"
APP_NAME     = "Visor v5.0 — Enterprise NOC"
ORGANIZATION = "Jasol Group"
AUTOR        = "Ing. Jeisson Alberto Sarmiento"
UBICACION    = "Saravena, Arauca, Colombia"

# ── INFRAESTRUCTURA L3 (Jasol Group) ──────────────────────────────────────

# MikroTik Core (Saravena)
MIKROTIK_HOST = "190.1.X.X"       # ← Reemplaza con IP real del Core
MIKROTIK_USER = "admin"
MIKROTIK_PASS = "Js92112751000"   # ← Cambiar tras primer uso

# Proxmox VE
PROXMOX_HOST        = "10.0.0.X"  # ← IP real del servidor Proxmox
PROXMOX_USER        = "root@pam"
PROXMOX_PASS        = ""          # Solo para API básica
PROXMOX_TOKEN_ID    = "root@pam!visor"   # Crear en: Datacenter > API Tokens
PROXMOX_TOKEN_SECRET = ""                # ← Pegar el secret aquí tras crearlo

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
SYNC_INTERVAL   = 300  # segundos

# ── COLORES ───────────────────────────────────────────────────────────────
COLORES_ACTIVOS = True
