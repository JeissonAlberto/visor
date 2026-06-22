# ─────────────────────────────────────────────
#  Visor — Configuración SMTP para alertas
#
#  Usa una Contraseña de Aplicación de Gmail:
#  https://myaccount.google.com/apppasswords
# ─────────────────────────────────────────────

SMTP_SERVER  = "smtp.gmail.com"
SMTP_PORT    = 465
SMTP_USER    = "tucorreo@gmail.com"        # ← tu correo de envío
SMTP_PASS    = "xxxx xxxx xxxx xxxx"       # ← contraseña de aplicación
DESTINATARIO = "destinatario@empresa.com"  # ← quién recibe las alertas

# ── Configuración de alertas ──
ASUNTO_CAIDA      = "[VISOR] ⚠️ Dispositivo CAÍDO: {nombre}"
ASUNTO_RECUPERADO = "[VISOR] ✅ Dispositivo RECUPERADO: {nombre}"
