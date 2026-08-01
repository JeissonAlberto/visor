# ─────────────────────────────────────────────
#  Visor — Configuración SMTP para alertas
#
#  Las credenciales se leen desde variables de entorno o desde
#  config/smtp_config_local.py (generado por el asistente y excluido de Git).
#  Nunca guardes contraseñas en este archivo.
# ─────────────────────────────────────────────

import os

SMTP_SERVER  = os.getenv("VISOR_SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT    = int(os.getenv("VISOR_SMTP_PORT", "465"))
SMTP_USER    = os.getenv("VISOR_SMTP_USER", "")
SMTP_PASS    = os.getenv("VISOR_SMTP_PASS", "")
DESTINATARIO = os.getenv("VISOR_SMTP_DESTINATARIO", "")

# ── Configuración de alertas ──
ASUNTO_CAIDA      = "[VISOR] ⚠️ Dispositivo CAÍDO: {nombre}"
ASUNTO_RECUPERADO = "[VISOR] ✅ Dispositivo RECUPERADO: {nombre}"

# El asistente puede crear este módulo local, sin versionarlo.
try:
    from config.smtp_config_local import (  # type: ignore
        SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, DESTINATARIO,
    )
except ModuleNotFoundError:
    pass
except ImportError as exc:
    raise RuntimeError("La configuración SMTP local no es válida") from exc
