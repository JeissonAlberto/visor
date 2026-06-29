# ─────────────────────────────────────────────
#  Visor — Configuración general
#  Edita este archivo para personalizar Visor
# ─────────────────────────────────────────────

VERSION      = "4.0.0"
APP_NAME     = "Visor v4.0 Command Center Edition"
ORGANIZATION = "Jasol Group"
AUTOR        = "Ing. Jeisson Alberto Sarmiento"
UBICACION    = "Saravena, Arauca, Colombia"

# ── CONFIGURACIÓN DE INFRAESTRUCTURA (Jasol Group) ──────────────

# MikroTik Core
MIKROTIK_HOST = "190.1.X.X"  # IP del Core en Saravena
MIKROTIK_USER = "admin"
MIKROTIK_PASS = "Js92112751000"

# Proxmox Virtualization
PROXMOX_HOST = "10.0.0.X"
PROXMOX_USER = "root@pam"
PROXMOX_PASS = "Js92112751000"

# Dashboard Sync (UI UX Pro Max)
DASHBOARD_URL = "https://site.zapia.com/sfxt00vr"
SYNC_INTERVAL = 300  # 5 minutos

# ── Intervalo de monitoreo continuo (segundos) ──
INTERVALO_MONITOREO = 60

# ── Ping ──
PING_COUNT   = 3       # bajamos a 3 para optimizar velocidad sin perder precisión
PING_TIMEOUT = 1       # bajamos a 1 para monitoreo LAN, es suficiente

# ── Reportes ──
GUARDAR_REPORTES  = True          # guardar reporte en /reports después de cada escaneo
FORMATO_REPORTE   = "txt"         # "txt" | "json"
MAX_REPORTES      = 20            # máximo de reportes guardados (elimina los más viejos)

# ── Alertas por correo ──
ALERTAS_EMAIL_ACTIVAS = True

# ── Colores en consola ──
COLORES_ACTIVOS = True
