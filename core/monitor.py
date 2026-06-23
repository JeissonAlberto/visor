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

def detectar_red_local() -> tuple[str, str, str]:
    """
    Detecta la IP local, el gateway y el rango CIDR.
    Devuelve (ip_local, gateway, rango_cidr) ej: ("192.168.1.5", "192.168.1.1", "192.168.1.0/24")
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

    # Optimizacion: Si hay dispositivos por MAC sin IP conocida, 
    # hacemos un escaneo rápido del rango para poblar la tabla ARP.
    necesita_arp = any(d.get("mac") and not d.get("ip") for d in dispositivos)
    if necesita_arp:
        _, _, rango = detectar_red_local()
        # Escaneo ultra-rápido (timeout bajo) solo para refrescar ARP
        escanear_rango(rango, max_workers=100)

    resultados = []
    # Usar hilos para escanear dispositivos LAN en paralelo y optimizar tiempo
    def procesar_dispositivo(dev):
        ip, metodo = _resolver_direccion(dev)
        if ip:
            online, lat = hacer_ping(ip, count=PING_COUNT, timeout=PING_TIMEOUT)
        else:
            online, lat = False, None

        return {
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

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        resultados = list(executor.map(procesar_dispositivo, dispositivos))

    return resultados


# ── Monitoreo continuo ────────────────────────────────────────────────────

def monitoreo_continuo(intervalo: int = 60, callback=None):
    """
    Monitoreo continuo optimizado para modo NOC Dashboard.
    """
    import time
    from core.colores import ok, fallo, info, warn, dim, separador, resaltar

    estados_anteriores: dict = {}
    ciclo = 0

    # Detectar red una sola vez al inicio si no hay config
    tiene_config_real = any(d.get("ip","").strip() or d.get("mac","").strip() for d in DISPOSITIVOS)
    if not tiene_config_real:
        print(f"\n  {info('Detectando red local automáticamente...')}")
        ip_local, gateway, rango = detectar_red_local()
        print(f"  {dim('IP local: ' + str(ip_local) + '  |  Gateway: ' + str(gateway) + '  |  Rango: ' + rango)}\n")

    while True:
        ciclo += 1
        t_inicio = time.time()
        ahora = datetime.now().strftime("%H:%M:%S")
        separador(f"Ciclo {ciclo} — {ahora}")

        # ── 1. Escaneo de dispositivos LAN (Multithreaded) ─────────
        resultados = escanear_dispositivos()
        caidos_lan = []
        
        # Mostrar resumen de LAN primero
        up_lan = sum(1 for r in resultados if r["online"])
        tot_lan = len(resultados)
        color_lan = ok if up_lan == tot_lan else (warn if up_lan > 0 else fallo)
        print(f"  Red LAN: {color_lan(f'{up_lan}/{tot_lan} dispositivos activos')}")

        for r in resultados:
            nombre   = r["nombre"]
            estado   = r["estado"]
            anterior = estados_anteriores.get(nombre)

            if estado == "UP":
                # En modo dashboard solo mostramos detalles si el usuario quiere o si cambió de estado
                # pero para Jeisson, mostramos una lista compacta
                lat_s = f"{r['latencia']}ms" if r["latencia"] else "—"
                print(f"    {ok('●')} {nombre:<20} {r['ip']:<15} {dim(lat_s)}")
                
                if anterior == "DOWN":
                    enviar_alerta(tipo="recuperado", nombre=nombre, ip=r["ip"],
                                  detalles=f"Recuperado a las {ahora}. Latencia: {lat_s}")
            else:
                print(f"    {fallo('●')} {nombre:<20} {r['ip']:<15} {fallo('SIN RESPUESTA')}")
                caidos_lan.append(nombre)
                if anterior != "DOWN":
                    enviar_alerta(tipo="caida", nombre=nombre, ip=r["ip"],
                                  detalles=f"Caída detectada a las {ahora}")

            estados_anteriores[nombre] = estado

        # ── 2. Servicios web ─────────────────────────────────────────
        try:
            from core.web_service import escanear_por_categorias
            print(f"\n  Servicios Web:")
            categorias = escanear_por_categorias()
            web_caidos = []
            for cat, servicios in categorias.items():
                up_w  = sum(1 for s in servicios if s.get("online"))
                tot_w = len(servicios)
                color_cat = ok if up_w == tot_w else (warn if up_w > 0 else fallo)
                
                # Vista compacta por categoría
                print(f"    {cat:<22} {color_cat(f'{up_w}/{tot_w}')}", end=" ")
                # Solo mostrar fallos específicos
                caidos_en_cat = [s.get("nombre") for s in servicios if not s.get("online")]
                if caidos_en_cat:
                    web_caidos.extend(caidos_en_cat)
                    print(fallo(f" (Falla: {', '.join(caidos_en_cat)})"))
                else:
                    print(ok(" ONLINE"))
                    
        except Exception as e:
            print("  " + warn(f"Servicios web: error ({e})"))

        # ── 3. Resumen y espera ────────────────────────────────────
        t_total = round(time.time() - t_inicio, 1)
        print(f"\n  {dim(f'Escaneo completado en {t_total}s')}")
        
        if callback:
            callback(resultados)

        espera = max(1, intervalo - int(t_total))
        print(f"  {dim(f'Próximo ciclo en {espera}s... (Ctrl+C para salir)')}")
        
        try:
            time.sleep(espera)
        except KeyboardInterrupt:
            print(f"\n\n  {resaltar('Monitoreo detenido por el usuario.')}\n")
            break
