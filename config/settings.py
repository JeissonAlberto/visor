# ─────────────────────────────────────────────
#  Visor — Configuración general
#  Edita este archivo para personalizar Visor
# ─────────────────────────────────────────────

VERSION      = "2.9.0"
APP_NAME     = "Visor v2.9 Guardian-AI Edition"
ORGANIZATION = "Jasol Group"
AUTOR        = "Ing. Jeisson Alberto Sarmiento"
UBICACION    = "Saravena, Arauca, Colombia"

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
