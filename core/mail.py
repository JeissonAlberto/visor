"""
core/mail.py — Envío de alertas por correo electrónico.
"""

import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime
from config.smtp_config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS, DESTINATARIO
from config.smtp_config import ASUNTO_CAIDA, ASUNTO_RECUPERADO
from config.settings import ALERTAS_EMAIL_ACTIVAS


def enviar_correo(asunto: str, cuerpo: str) -> bool:
    """Envía un correo. Devuelve True si fue exitoso.

    Las alertas se omiten silenciosamente cuando están deshabilitadas o
    incompletas; así un despliegue nuevo no intenta autenticarse contra SMTP
    con credenciales vacías.
    """
    if not ALERTAS_EMAIL_ACTIVAS:
        return False

    # La configuración llega desde variables de entorno o el archivo local.
    # Validar todos los campos evita conexiones inútiles y errores confusos.
    if not all((SMTP_SERVER, SMTP_PORT, SMTP_USER.strip(), SMTP_PASS,
                DESTINATARIO.strip())):
        return False  # No configurado

    try:
        msg = EmailMessage()
        msg["From"]    = SMTP_USER
        msg["To"]      = DESTINATARIO
        msg["Subject"] = asunto
        msg.set_content(cuerpo)

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ctx) as smtp:
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        return True
    except Exception:
        return False


def enviar_alerta(tipo: str, nombre: str, ip: str, detalles: str = "") -> bool:
    """
    Envía alerta de caída o recuperación.
    tipo: "caida" | "recuperado"
    """
    ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    if tipo == "caida":
        asunto = ASUNTO_CAIDA.format(nombre=nombre)
        cuerpo = (
            f"[VISOR — Jasol Group]\n"
            f"─────────────────────────────\n"
            f"⚠️  DISPOSITIVO CAÍDO\n\n"
            f"Nombre:    {nombre}\n"
            f"Dirección: {ip}\n"
            f"Hora:      {ts}\n"
            f"Detalle:   {detalles}\n"
            f"─────────────────────────────\n"
            f"Este es un mensaje automático de Visor.\n"
        )
    else:
        asunto = ASUNTO_RECUPERADO.format(nombre=nombre)
        cuerpo = (
            f"[VISOR — Jasol Group]\n"
            f"─────────────────────────────\n"
            f"✅  DISPOSITIVO RECUPERADO\n\n"
            f"Nombre:    {nombre}\n"
            f"Dirección: {ip}\n"
            f"Hora:      {ts}\n"
            f"Detalle:   {detalles}\n"
            f"─────────────────────────────\n"
            f"Este es un mensaje automático de Visor.\n"
        )

    return enviar_correo(asunto, cuerpo)
