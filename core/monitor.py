"""
core/monitor.py — Escaneo de dispositivos.
Si no hay dispositivos configurados, detecta automáticamente la red local.
"""

import ipaddress
import re
import socket
import concurrent.futures
from datetime import datetime
from core.red import hacer_ping, buscar_ip_por_mac, resolver_host, escanear_rango
from core.mail import enviar_alerta
from config.device import DISPOSITIVOS
from config.settings import PING_COUNT, PING_TIMEOUT


# ── Detección automática de red ───────────────────────────────────────────

def _rango_desde_rutas(ip_local: str | None, salida: str) -> str | None:
    """Obtiene la ruta conectada que contiene ``ip_local``."""
    try:
        direccion = ipaddress.ip_address(ip_local)
    except (ValueError, TypeError):
        return None

    redes = []
    for cidr in re.findall(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}", salida or ""):
        try:
            red = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        if red.version == direccion.version and direccion in red:
            redes.append(red)
    if not redes:
        return None
    return str(max(redes, key=lambda red: red.prefixlen))


def _rango_desde_mascara(ip_local: str | None, mascara: str | None) -> str | None:
    """Construye una red desde la máscara de interfaz de Windows."""
    if not ip_local or not mascara:
        return None
    try:
        return str(ipaddress.ip_network(f"{ip_local}/{mascara}", strict=False))
    except ValueError:
        return None


def detectar_red_local() -> tuple[str, str, str]:
    """
    Detecta la IP local, el gateway y el rango CIDR.
    Devuelve (ip_local, gateway, rango_cidr) ej: ("192.168.1.5", "192.168.1.1", "192.168.1.0/24")
    """
    import subprocess, platform

    ip_local  = None
    gateway   = None
    rango_detectado = None
    sistema   = platform.system().lower()

    try:
        # IP local — conectar a DNS externo sin enviar datos. El context
        # manager también cierra el socket si connect() falla.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
    except (OSError, IndexError, TypeError):
        ip_local = "127.0.0.1"

    try:
        if sistema == "windows":
            r = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=5)
            m = re.search(r"(?:Puerta de enlace|Default Gateway)[^\d]+([\d.]+)", r.stdout, re.IGNORECASE)
            gateway = m.group(1) if m else None
            mascara = re.search(r"(?:Máscara de subred|Subnet Mask)[^\d]+([\d.]+)", r.stdout, re.IGNORECASE)
            rango_detectado = _rango_desde_mascara(
                ip_local, mascara.group(1) if mascara else None
            )
        else:
            r = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=5)
            m = re.search(r"default via ([\d.]+)", r.stdout)
            gateway = m.group(1) if m else None
            rango_detectado = _rango_desde_rutas(ip_local, r.stdout)
    except (OSError, subprocess.SubprocessError):
        gateway = None

    # Si el sistema no expone la máscara, conserva un fallback seguro.
    if rango_detectado:
        rango = rango_detectado
    elif ip_local and ip_local != "127.0.0.1":
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
    except ValueError:
        # Solo se espera un rango inválido o demasiado grande; otros errores
        # deben propagarse para no ocultar fallos del descubrimiento.
        pass

    return dispositivos


# ── Resolución de dirección ───────────────────────────────────────────────

def _resolver_direccion(dispositivo: dict) -> tuple:
    """Resuelve una entrada de dispositivo sin asumir tipos perfectos."""
    mac_val = dispositivo.get("mac", "")
    ip_val = dispositivo.get("ip", "")
    mac = mac_val.strip() if isinstance(mac_val, str) else ""
    ip = ip_val.strip() if isinstance(ip_val, str) else ""

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

def escanear_dispositivos(dispositivos: list | None = None, auto_descubrir: bool = True) -> list:
    """
    Escanea la lista de dispositivos.
    Si auto_descubrir es True, además agrega dispositivos activos detectados en la red.
    """
    if not dispositivos:
        dispositivos = list(DISPOSITIVOS)
    else:
        # Copiar siempre: el descubrimiento automático agrega entradas y no
        # debe mutar una lista recibida por el llamador.
        dispositivos = list(dispositivos)
    # Una entrada mal formada en el archivo de configuración no debe detener
    # el monitoreo completo.
    dispositivos = [d for d in dispositivos if isinstance(d, dict)]

    # 1. Detectar red actual para ver si los dispositivos configurados son coherentes
    ip_local, gateway_real, rango_actual = detectar_red_local()

    # 2. Si auto_descubrir está activo, mezclamos la config con lo que encontremos en vivo
    if auto_descubrir:
        en_vivo = _descubrir_dispositivos_red()
        # Combinar evitando duplicados por IP
        ips_configuradas = {d.get("ip") for d in dispositivos if d.get("ip")}
        for d_vivo in en_vivo:
            if d_vivo["ip"] not in ips_configuradas:
                dispositivos.append(d_vivo)
                ips_configuradas.add(d_vivo["ip"])

    # Optimizacion ARP...
    necesita_arp = any(d.get("mac") and not d.get("ip") for d in dispositivos)
    if necesita_arp:
        escanear_rango(rango_actual, max_workers=100)

    # ...resto del procesamiento multihilo...
    resultados = []
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
    estados_web_anteriores: dict = {}
    ciclo = 0

    # Detectar red una sola vez al inicio si no hay config
    tiene_config_real = any(
        isinstance(d, dict)
        and any(isinstance(d.get(campo), str) and d.get(campo).strip()
                for campo in ("ip", "mac"))
        for d in DISPOSITIVOS
    )
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

                # Alertar solo en cambios de estado, no en cada ciclo.
                for servicio in servicios:
                    clave = servicio.get("url") or servicio.get("nombre")
                    estado = "UP" if servicio.get("online") else "DOWN"
                    anterior = estados_web_anteriores.get(clave)
                    if estado == "DOWN" and anterior != "DOWN":
                        enviar_alerta(
                            tipo="caida",
                            nombre=servicio.get("nombre", clave),
                            ip=clave,
                            detalles=f"HTTP: {servicio.get('http') or 'sin respuesta'}; {servicio.get('error') or 'servicio no disponible'}",
                        )
                    elif estado == "UP" and anterior == "DOWN":
                        enviar_alerta(
                            tipo="recuperado",
                            nombre=servicio.get("nombre", clave),
                            ip=clave,
                            detalles=f"HTTP: {servicio.get('http') or 'OK'}; latencia: {servicio.get('latencia') or '—'} ms",
                        )
                    estados_web_anteriores[clave] = estado

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
