# ─────────────────────────────────────────────
#  Visor — Configuración general
#  Edita este archivo para personalizar Visor
# ─────────────────────────────────────────────

VERSION = "2.0.0"
APP_NAME = "Visor"
ORGANIZATION = "Jasol Group"

# ── Intervalo de monitoreo continuo (segundos) ──
INTERVALO_MONITOREO = 60

# ── Ping ──
PING_COUNT   = 4       # paquetes por host
PING_TIMEOUT = 2       # segundos de espera por ping

# ── Reportes ──
GUARDAR_REPORTES  = True          # guardar reporte en /reports después de cada escaneo
FORMATO_REPORTE   = "txt"         # "txt" | "json"
MAX_REPORTES      = 20            # máximo de reportes guardados (elimina los más viejos)

# ── Alertas por correo ──
# Configura las credenciales en config/smtp_config.py
ALERTAS_EMAIL_ACTIVAS = True

# ── Colores en consola ──
COLORES_ACTIVOS = True
