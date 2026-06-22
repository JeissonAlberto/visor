# ─────────────────────────────────────────────────────
#  Visor — Dispositivos a monitorear
#
#  Campos por dispositivo:
#    nombre  : Nombre descriptivo
#    ip      : IP fija (si la tiene). Dejar "" si usas MAC.
#    mac     : Dirección MAC (para detectar IP dinámica via ARP).
#              Dejar "" si usas IP o dominio directamente.
#    tipo    : "lan" | "web" | "ups" | "camara" | "servidor"
#    grupo   : Etiqueta para agrupar (ej: "Oficina", "Torre Norte")
#
#  Puedes mezclar: algunos por IP, otros por MAC, otros por dominio.
# ─────────────────────────────────────────────────────

DISPOSITIVOS = [
    # ── Equipos de red ──────────────────────────────
    {
        "nombre": "Gateway / Router",
        "ip":     "192.168.1.1",
        "mac":    "",
        "tipo":   "lan",
        "grupo":  "Red principal",
    },
    {
        "nombre": "AP TP-Link 1",
        "ip":     "",
        "mac":    "B0:BE:76:2D:E1:59",
        "tipo":   "lan",
        "grupo":  "Red principal",
    },
    {
        "nombre": "AP TP-Link 2",
        "ip":     "",
        "mac":    "B0:BE:76:2D:E1:31",
        "tipo":   "lan",
        "grupo":  "Red principal",
    },

    # ── Servidores / Servicios públicos ─────────────
    # (dejar mac vacío, usar ip o dominio como ip)
    # {
    #     "nombre": "Servidor Web",
    #     "ip":     "mipagina.com",
    #     "mac":    "",
    #     "tipo":   "servidor",
    #     "grupo":  "Producción",
    # },
]

# ── Servicios web a verificar (HTTP) ────────────────
SERVICIOS_WEB = [
    {"nombre": "Google DNS",    "url": "https://www.google.com"},
    {"nombre": "Cloudflare",    "url": "https://www.cloudflare.com"},
    # Agrega los tuyos:
    # {"nombre": "Mi sitio",    "url": "https://mipagina.com"},
]

# ── Rango IP para escaneo automático ────────────────
# Visor escaneará todas las IPs de este rango buscando hosts activos
RANGO_SCAN = "192.168.1.0/24"
