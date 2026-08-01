"""
ui/setup_wizard.py — Asistente interactivo de primera configuración.
"""

from core.colores import banner, separador, titulo, info, ok, warn, dim, resaltar
import re


def setup_wizard():
    banner()
    separador("Asistente de configuración — Visor v2.0")

    print(f"""
  {info('Este asistente te ayudará a configurar Visor en minutos.')}
  Iremos paso a paso. Puedes saltar cualquier sección con Enter.
""")

    dispositivos = _paso_dispositivos()
    servicios    = _paso_web()
    smtp         = _paso_smtp()
    rango        = _paso_rango()

    # Escribir config/device.py
    _escribir_device(dispositivos, servicios, rango)

    # Escribir config/smtp_config.py (solo si se configuró)
    if smtp:
        _escribir_smtp(smtp)

    separador()
    print(f"\n  {ok('¡Configuración completada!')}")
    print(f"  {dim('Archivos actualizados: config/device.py' + (' · config/smtp_config_local.py' if smtp else ''))}")
    print(f"\n  Ahora ejecuta: {resaltar('python main.py')}\n")


def _paso_dispositivos():
    separador("Paso 1 — Dispositivos de red")
    print(f"\n  {info('Agrega los equipos que quieres monitorear.')}")
    print(f"  {dim('Usa IP si es fija, o MAC si la IP puede cambiar.')}\n")

    dispositivos = []
    while True:
        print(f"  {resaltar(f'Dispositivo {len(dispositivos)+1}')} (Enter en nombre para terminar)")
        nombre = input("    Nombre (ej: Router principal): ").strip()
        if not nombre:
            break
        ip  = input("    IP o dominio  (ej: 192.168.1.1): ").strip()
        mac = input("    MAC           (ej: B0:BE:76:...) — opcional: ").strip()
        grp = input("    Grupo         (ej: Oficina)      — opcional: ").strip() or "General"
        dispositivos.append({"nombre": nombre, "ip": ip, "mac": mac, "tipo": "lan", "grupo": grp})
        print(f"  {ok(f'{nombre} agregado.')}\n")

    if not dispositivos:
        print(f"  {dim('Sin dispositivos. Se usarán los de ejemplo.')}")
    return dispositivos


def _paso_web():
    separador("Paso 2 — Servicios web")
    print(f"\n  {info('Agrega URLs a verificar (dominios o links completos).')}\n")

    servicios = []
    while True:
        print(f"  {resaltar(f'Servicio {len(servicios)+1}')} (Enter en nombre para terminar)")
        nombre = input("    Nombre (ej: Mi sitio web): ").strip()
        if not nombre:
            break
        url = input("    URL   (ej: https://miempresa.com): ").strip()
        if url and not url.startswith("http"):
            url = "https://" + url
        servicios.append({"nombre": nombre, "url": url})
        print(f"  {ok(f'{nombre} agregado.')}\n")

    return servicios


def _paso_smtp():
    separador("Paso 3 — Alertas por correo (opcional)")
    print(f"\n  {info('Configura un correo Gmail para recibir alertas automáticas.')}")
    print(f"  {dim('Necesitas una Contraseña de Aplicación: myaccount.google.com/apppasswords')}\n")

    activar = input("  ¿Configurar alertas por correo? [s/N]: ").strip().lower()
    if activar != "s":
        return None

    usuario = input("  Correo de envío  (Gmail): ").strip()
    clave   = input("  Contraseña de aplicación (16 chars): ").strip()
    destino = input("  Correo destinatario: ").strip()

    return {"usuario": usuario, "clave": clave, "destino": destino}


def _paso_rango():
    separador("Paso 4 — Rango IP para escaneo")
    print(f"\n  {info('Define el rango de red a escanear automáticamente.')}")
    print(f"  {dim('Ejemplo: 192.168.1.0/24 cubre las IPs .1 a .254')}\n")
    rango = input("  Rango CIDR [192.168.1.0/24]: ").strip() or "192.168.1.0/24"
    return rango


def _escribir_device(dispositivos, servicios, rango):
    from pathlib import Path

    dev_lines = []
    if dispositivos:
        for d in dispositivos:
            dev_lines.append(f"""    {{
        "nombre": {repr(d["nombre"])},
        "ip":     {repr(d["ip"])},
        "mac":    {repr(d["mac"])},
        "tipo":   "lan",
        "grupo":  {repr(d["grupo"])},
    }},""")
    else:
        dev_lines = [
            '    {"nombre": "Gateway / Router", "ip": "192.168.1.1", "mac": "", "tipo": "lan", "grupo": "Red principal"},',
            '    {"nombre": "AP TP-Link 1",     "ip": "",            "mac": "B0:BE:76:2D:E1:59", "tipo": "lan", "grupo": "Red principal"},',
        ]

    web_lines = []
    if servicios:
        for s in servicios:
            web_lines.append(f'    {{"nombre": {repr(s["nombre"])}, "url": {repr(s["url"])}}},')
    else:
        web_lines = [
            '    {"nombre": "Google", "url": "https://www.google.com"},',
            '    {"nombre": "Cloudflare", "url": "https://www.cloudflare.com"},',
        ]

    contenido = f"""# Generado por Visor Setup Wizard
DISPOSITIVOS = [
{chr(10).join(dev_lines)}
]

SERVICIOS_WEB = [
{chr(10).join(web_lines)}
]

RANGO_SCAN = {repr(rango)}
"""
    path = Path("config/device.py")
    path.write_text(contenido, encoding="utf-8")


def _escribir_smtp(smtp):
    """Guarda la configuración SMTP en un módulo local ignorado por Git."""
    from pathlib import Path

    contenido = f"""# Generado por Visor Setup Wizard — NO versionar
SMTP_SERVER  = "smtp.gmail.com"
SMTP_PORT    = 465
SMTP_USER    = {smtp["usuario"]!r}
SMTP_PASS    = {smtp["clave"]!r}
DESTINATARIO = {smtp["destino"]!r}
"""
    path = Path("config/smtp_config_local.py")
    path.write_text(contenido, encoding="utf-8")
