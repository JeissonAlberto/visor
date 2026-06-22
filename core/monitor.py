"""
core/monitor.py — Escaneo de dispositivos.
Si no hay dispositivos configurados, detecta automáticamente la red local.
"""

import ipaddress
import socket
import concurrent.futures
from datetime import datetime
from core.red import hacer_ping, buscar_ip_por_mac, resolver_host, escanear_rango
from core.mail import enviar_alerta
from config.device import DISPOSITIVOS
from config.settings import PING_COUNT, PING_TIMEOUT


# ── Detección automática de red ───────────────────────────────────────────

def detectar_red_local() -> tuple[str, str]:
    """
    Detecta la IP local y el gateway.
    Devuelve (ip_local, rango_cidr) ej: ("192.168.1.5", "192.168.1.0/24")
    """
    import subprocess, platform, re

    ip_local  = None
    gateway   = None
    sistema   = platform.system().lower()

    try:
        # IP local — conectar a DNS externo sin enviar datos
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
    except Exception:
        ip_local = "127.0.0.1"

    try:
        if sistema == "windows":
            r = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=5)
            m = re.search(r"(?:Puerta de enlace|Default Gateway)[^\d]+([\d.]+)", r.stdout, re.IGNORECASE)
            gateway = m.group(1) if m else None
        else:
            r = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=5)
            m = re.search(r"default via ([\d.]+)", r.stdout)
            gateway = m.group(1) if m else None
    except Exception:
        gateway = None

    # Derivar rango /24 desde la IP local
    if ip_local and ip_local != "127.0.0.1":
        partes = ip_local.split(".")
        rango  = ".".join(partes[:3]) + ".0/24"
    else:
        rango = "192.168.1.0/24"

    return ip_local, gateway, rango


def _descubrir_dispositivos_red() -> list[dict]:
    """
    Escanea la red local automáticamente y construye la lista de dispositivos.
    Agrega gateway, IP local e IPs activas detectadas.
    """
    ip_local, gateway, rango = detectar_red_local()
    dispositivos = []

    # 1. Gateway
    if gateway:
        dispositivos.append({
            "nombre": "Gateway / Router",
            "ip":     gateway,
            "mac":    "",
            "tipo":   "lan",
            "grupo":  "Red detectada",
        })

    # 2. Esta máquina
    if ip_local and ip_local != "127.0.0.1" and ip_local != gateway:
        dispositivos.append({
            "nombre": "Este equipo",
            "ip":     ip_local,
            "mac":    "",
            "tipo":   "lan",
            "grupo":  "Red detectada",
        })

    # 3. Escanear rango para encontrar más hosts (rápido: /24 con timeout bajo)
    try:
        activos = escanear_rango(rango, max_workers=80)
        conocidas = {gateway, ip_local}
        count = 0
        for h in activos:
            if not h.get("activo"):
                continue
            if h["ip"] in conocidas:
                continue
            nombre = h.get("hostname") or "Host " + h["ip"].split(".")[-1]
            dispositivos.append({
                "nombre": nombre,
                "ip":     h["ip"],
                "mac":    "",
                "tipo":   "lan",
                "grupo":  "Red detectada",
            })
            count += 1
            if count >= 30:   # máximo 30 hosts dinámicos
                break
    except Exception:
        pass

    return dispositivos


# ── Resolución de dirección ───────────────────────────────────────────────

def _resolver_direccion(dispositivo: dict) -> tuple:
    mac = dispositivo.get("mac", "").strip()
    ip  = dispositivo.get("ip", "").strip()

    if mac:
        ip_arp = buscar_ip_por_mac(mac)
        if ip_arp:
            return ip_arp, "ARP"
        if ip:
            return ip, "IP (MAC no en ARP)"
        return None, "MAC no encontrada"

    if ip:
        ip_res = resolver_host(ip)
        if ip_res and ip_res != ip:
            return ip_res, "DNS"
        return ip, "IP directa"

    return None, "Sin dirección"


# ── Escaneo ───────────────────────────────────────────────────────────────

def escanear_dispositivos(dispositivos: list | None = None) -> list:
    """
    Escanea la lista de dispositivos.
    Si está vacía o no se pasa, descubre la red automáticamente.
    """
    if not dispositivos:
        dispositivos = DISPOSITIVOS

    # Si la config está vacía o solo tiene ejemplos sin IP/MAC útil,
    # caer en detección automática
    tiene_config_real = any(
        d.get("ip","").strip() or d.get("mac","").strip()
        for d in dispositivos
    )
    if not tiene_config_real:
        dispositivos = _descubrir_dispositivos_red()

    resultados = []
    for dev in dispositivos:
        ip, metodo = _resolver_direccion(dev)

        if ip:
            online, lat = hacer_ping(ip, count=PING_COUNT, timeout=PING_TIMEOUT)
        else:
            online, lat = False, None

        resultado = {
            "nombre":   dev.get("nombre", "Host"),
            "ip":       ip or "—",
            "mac":      dev.get("mac", ""),
            "tipo":     dev.get("tipo", "lan"),
            "grupo":    dev.get("grupo", "General"),
            "online":   online,
            "estado":   "UP" if online else "DOWN",
            "latencia": round(lat, 1) if lat else None,
            "metodo":   metodo,
            "ts":       datetime.now().isoformat(timespec="seconds"),
        }
        resultados.append(resultado)

    return resultados


# ── Monitoreo continuo ────────────────────────────────────────────────────

def monitoreo_continuo(intervalo: int = 60, callback=None):
    """
    Monitoreo continuo. Detecta la red automáticamente si no hay config manual.
    """
    import time
    from core.colores import ok, fallo, info, warn, dim, separador, resaltar

    estados_anteriores: dict = {}
    ciclo = 0

    # Detectar red una sola vez al inicio
    tiene_config_real = any(
        d.get("ip","").strip() or d.get("mac","").strip()
        for d in DISPOSITIVOS
    )

    if not tiene_config_real:
        print(f"\n  {info('Detectando red local automáticamente...')}")
        ip_local, gateway, rango = detectar_red_local()
        print(f"  {dim('IP local: ' + str(ip_local) + '  |  Gateway: ' + str(gateway) + '  |  Rango: ' + rango)}\n")

    while True:
        ciclo += 1
        separador("Ciclo " + str(ciclo) + " — " + datetime.now().strftime("%H:%M:%S"))

        resultados = escanear_dispositivos()
        caidos = []

        for r in resultados:
            nombre   = r["nombre"]
            estado   = r["estado"]
            anterior = estados_anteriores.get(nombre)

            if estado == "UP":
                lat_s = str(r["latencia"]) + " ms" if r["latencia"] else "—"
                print(ok(nombre + " (" + r["ip"] + ") — " + lat_s))
                if anterior == "DOWN":
                    enviar_alerta(tipo="recuperado", nombre=nombre, ip=r["ip"],
                                  detalles="Latencia: " + str(r["latencia"]) + " ms")
            else:
                print(fallo(nombre + " (" + r["ip"] + ") — Sin respuesta"))
                caidos.append(nombre)
                if anterior != "DOWN":
                    enviar_alerta(tipo="caida", nombre=nombre, ip=r["ip"],
                                  detalles="No responde a ping")

            estados_anteriores[nombre] = estado

        if callback:
            callback(resultados)

        up   = len(resultados) - len(caidos)
        total = len(resultados)
        print("\n  " + resaltar(str(up) + "/" + str(total) + " dispositivos en línea"))

        if caidos:
            print("  " + warn("Caídos: " + ", ".join(caidos)))

        print("\n  " + dim("Próximo ciclo en " + str(intervalo) + "s... (Ctrl+C para salir)"))
        try:
            time.sleep(intervalo)
        except KeyboardInterrupt:
            print("\n\n  Monitoreo detenido.\n")
            break
