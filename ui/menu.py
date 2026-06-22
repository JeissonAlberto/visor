"""
ui/menu.py — Menú principal de Visor v2.1
Jasol Group · Ing. Jeisson Alberto Sarmiento · Saravena, Arauca, Colombia
"""

from datetime import datetime
from core.colores import (
    banner, separador, titulo, info, ok, fallo, warn,
    dim, resaltar, azul, naranja, tabla_estado, firma
)
from config.settings import INTERVALO_MONITOREO, VERSION, AUTOR, ORGANIZATION, UBICACION


# ── Menú principal ────────────────────────────────────────────────────────

def menu_principal():
    banner()
    while True:
        print(f"\n  {titulo('MENÚ PRINCIPAL')}")
        separador()
        print(f"  {resaltar('1.')} 📡  Monitoreo continuo de red")
        print(f"  {resaltar('2.')} 🔍  Escaneo único de dispositivos")
        print(f"  {resaltar('3.')} 🌐  Verificar servicios web")
        print(f"  {resaltar('4.')} 📶  Test de calidad de internet")
        print(f"  {resaltar('5.')} 🗺️   Escanear rango IP")
        print(f"  {resaltar('6.')} 📋  Ver último reporte")
        print(f"  {resaltar('7.')} 🔌  Info de interfaces de red")
        print(f"  {resaltar('8.')} 🌍  Geolocalizar IP pública")
        print(f"  {resaltar('9.')} ⚙️   Configuración rápida")
        print(f"  {resaltar('0.')} ❌  Salir")
        separador()

        opcion = input(f"\n  {info('Elige una opción:')} ").strip()

        if   opcion == "1": _menu_monitoreo()
        elif opcion == "2": _escaneo_unico()
        elif opcion == "3": _menu_web()
        elif opcion == "4": _menu_internet()
        elif opcion == "5": _menu_rango()
        elif opcion == "6": _ver_reporte()
        elif opcion == "7": _info_interfaces()
        elif opcion == "8": _geolocalizacion_manual()
        elif opcion == "9": _configuracion_rapida()
        elif opcion == "0":
            print(f"\n  {dim('─'*50)}")
            print(f"  {dim('Creado por ' + AUTOR)}")
            print(f"  {dim('Pertenece a ' + ORGANIZATION + '  ·  ' + UBICACION)}")
            print(f"  {dim('─'*50)}\n")
            break
        else:
            print(f"\n  {warn('Opción inválida. Intenta de nuevo.')}")


# ── 1. Monitoreo continuo ─────────────────────────────────────────────────

def _menu_monitoreo():
    from core.monitor import monitoreo_continuo
    banner()
    separador("Monitoreo continuo")
    print(f"\n  {info('Intervalo: ' + str(INTERVALO_MONITOREO) + 's   ·   Ctrl+C para detener')}\n")
    try:
        monitoreo_continuo(intervalo=INTERVALO_MONITOREO)
    except KeyboardInterrupt:
        pass


# ── 2. Escaneo único ──────────────────────────────────────────────────────

def _escaneo_unico():
    from core.monitor import escanear_dispositivos
    from utils.reportes import guardar_reporte

    separador("Escaneo de dispositivos")
    print(f"\n  {info('Escaneando la red...')}\n")

    resultados = escanear_dispositivos()
    up   = [r for r in resultados if r["online"]]
    down = [r for r in resultados if not r["online"]]

    tabla_estado(resultados)
    separador()
    print(f"  {ok(str(len(up)) + ' en línea')}   {fallo(str(len(down)) + ' caídos')}   {dim('Total: ' + str(len(resultados)))}")

    ruta = guardar_reporte({"ts": datetime.now().isoformat(), "dispositivos": resultados})
    if ruta:
        print(f"\n  {dim('Reporte guardado: ' + ruta.name)}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── 3. Servicios web ──────────────────────────────────────────────────────

def _menu_web():
    from core.web_service import escanear_por_categorias
    from utils.reportes import guardar_reporte

    separador("Verificar servicios web")
    print(f"\n  {info('Verificando DNS, redes sociales, IAs y tus servicios...')}")
    print(f"  {dim('Puede tardar 15-30 segundos')}\n")

    categorias = escanear_por_categorias()

    total_up = total_tot = 0
    for cat, servicios in categorias.items():
        up  = sum(1 for s in servicios if s.get("online"))
        tot = len(servicios)
        total_up  += up
        total_tot += tot

        icono = "✅" if up == tot else ("⚠️ " if up > 0 else "❌")
        separador(f"{cat}  {icono} {up}/{tot}")

        ancho = max((len(s["nombre"]) for s in servicios), default=10) + 2
        for s in servicios:
            nombre = s["nombre"]
            online = s.get("online")
            lat    = s.get("latencia")
            http   = s.get("http", "—")
            lat_s  = f"{lat:.1f} ms" if lat else "—"
            lat_c  = "✅" if lat and lat < 400 else "⚠️ "
            estado = ok("  UP  ") if online else fallo(" DOWN ")
            print(f"  {nombre:<{ancho}} [{estado}]  HTTP {http}  {lat_c} {lat_s}")

    separador()
    print(f"  TOTAL:  {ok(str(total_up) + '/' + str(total_tot) + ' servicios activos') if total_up == total_tot else warn(str(total_up) + '/' + str(total_tot) + ' servicios activos')}")

    ruta = guardar_reporte({"ts": datetime.now().isoformat(), "web": categorias})
    if ruta:
        print(f"  {dim('Reporte guardado: ' + ruta.name)}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── 4. Test de internet ───────────────────────────────────────────────────

def _menu_internet():
    from core.test_internet import medir_calidad
    from utils.reportes import guardar_reporte

    separador("Test de calidad de internet")
    print(f"\n  {info('Midiendo latencia, velocidad y throughput...')}")
    print(f"  {dim('(Esto puede tardar 20-40 segundos)')}\n")

    r = medir_calidad()

    cal = r.get("calidad", "—")
    cal_s = ok(cal) if cal == "EXCELENTE" else (ok(cal) if cal == "BUENA" else (warn(cal) if cal in ("REGULAR",) else fallo(cal)))

    separador()
    print(f"  {'Calidad:':<28} {cal_s}")
    separador()

    # Latencia
    print(f"\n  {resaltar('LATENCIA')}")
    lat_avg = r.get("lat_avg")
    lat_min = r.get("lat_min")
    lat_max = r.get("lat_max")
    jitter  = r.get("jitter")
    perdida = r.get("perdida", 0)
    _linea("Promedio:",           f"{lat_avg} ms" if lat_avg else "—",  lat_avg and lat_avg < 80)
    _linea("Mínima:",             f"{lat_min} ms" if lat_min else "—",  True)
    _linea("Máxima:",             f"{lat_max} ms" if lat_max else "—",  lat_max and lat_max < 150)
    _linea("Jitter:",             f"{jitter} ms"  if jitter  else "—",  jitter  and jitter  < 20)
    _linea("Pérdida de paquetes:",f"{perdida}%",                         perdida == 0)
    _linea("Pings OK / Total:",   f"{r.get('pings_ok')} / {r.get('total_pings')}", True)

    # Velocidad
    print(f"\n  {resaltar('VELOCIDAD')}")
    dl = r.get("descarga_mbps")
    ul = r.get("subida_mbps")
    fl = r.get("fuente_dl", "—")
    fu = r.get("fuente_ul", "—")
    _linea("Descarga:", f"{dl} Mbps  via {fl}" if dl else "No disponible", bool(dl))
    _linea("Subida:",   f"{ul} Mbps  via {fu}" if ul else "No disponible", bool(ul))

    # Throughput
    tp = r.get("throughput_mbps")
    ft = r.get("fuente_tp", "loopback")
    print(f"\n  {resaltar('THROUGHPUT TCP LOCAL')}")
    _linea("Stack de red:", f"{tp} Mbps  ({ft})" if tp else "—", bool(tp))

    # Hosts referencia
    print(f"\n  {resaltar('HOSTS DE REFERENCIA')}")
    for h in r.get("hosts", []):
        lat_h = h.get("latencia")
        estado_h = ok(f"{lat_h} ms") if lat_h and lat_h < 100 else (warn(f"{lat_h} ms") if lat_h else fallo("Sin respuesta"))
        print(f"  {h.get('nombre',''):<16} {h.get('ip',''):<12} {estado_h}")

    separador()
    ruta = guardar_reporte({"ts": datetime.now().isoformat(), "internet": r})
    if ruta:
        print(f"  {dim('Reporte guardado: ' + ruta.name)}")

    input(f"\n  {dim('Enter para continuar...')}")


def _linea(label, valor, bueno=True):
    icono = "✅" if bueno else "❌"
    print(f"  {label:<28} {icono} {valor}")


# ── 5. Escaneo de rango IP ────────────────────────────────────────────────

def _menu_rango():
    import socket
    from core.red import escanear_rango
    from core.web_service import geolocalizacion_ip
    from config.device import RANGO_SCAN

    separador("Escanear rango IP")

    # Autodetectar rango sugerido
    rango_auto = RANGO_SCAN
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        partes = ip_local.split(".")
        rango_auto = ".".join(partes[:3]) + ".0/24"
    except Exception:
        pass

    print(f"\n  {dim('Ejemplos: 192.168.1.0/24  |  10.0.0.0/24  |  172.16.0.0/24')}")
    print(f"  {dim('Enter para usar el rango detectado: ' + rango_auto)}")
    rango_input = input(f"\n  {info('Rango IP a escanear:')} ").strip()

    rango = rango_input if rango_input else rango_auto

    # Validar formato
    import ipaddress
    try:
        red = ipaddress.ip_network(rango, strict=False)
        total_ips = red.num_addresses - 2
    except ValueError:
        print(f"\n  {fallo('Rango inválido. Usa formato CIDR, ej: 192.168.1.0/24')}")
        input(f"\n  {dim('Enter para continuar...')}")
        return

    print(f"\n  {info('Escaneando ' + rango + ' (' + str(total_ips) + ' IPs)...')}")
    print(f"  {dim('Puede tardar 30-60 segundos...')}\n")

    resultados = escanear_rango(rango)
    activos    = [r for r in resultados if r.get("activo")]

    if activos:
        ancho_ip = 20
        print(f"  {resaltar('IP'):<{ancho_ip}} {resaltar('LATENCIA'):<20} {resaltar('HOSTNAME')}")
        print(f"  {dim('─'*65)}")
        for h in activos:
            lat_s    = f"{h['latencia']} ms" if h.get("latencia") else "—"
            hostname = h.get("hostname") or "—"
            color    = ok if h.get("latencia") and h["latencia"] < 50 else warn
            print(f"  {h['ip']:<{ancho_ip}} {color(lat_s):<30} {dim(hostname)}")
    else:
        print(f"  {warn('No se encontraron hosts activos en el rango.')}")

    separador()
    print(f"  {ok(str(len(activos)) + ' host(s) activos')} de {str(total_ips)} IPs escaneadas")

    # Geolocalización de IPs públicas
    publicas = [h["ip"] for h in activos if not _es_privada(h["ip"])]
    if publicas:
        print(f"\n  {info('Geolocalizando ' + str(len(publicas)) + ' IPs públicas...')}\n")
        print(f"  {resaltar('IP'):<20} {resaltar('PAÍS'):<22} {resaltar('CIUDAD'):<20} {resaltar('ISP')}")
        print(f"  {dim('─'*80)}")
        for ip in publicas:
            geo    = geolocalizacion_ip(ip)
            pais   = geo.get("pais", "?")
            ciudad = geo.get("ciudad", "?")
            isp    = geo.get("isp", "?")
            lat_g  = geo.get("lat")
            lon_g  = geo.get("lon")
            coord  = f"({lat_g}, {lon_g})" if lat_g and lon_g else ""
            print(f"  {ip:<20} {pais:<22} {ciudad:<20} {isp}")
            if coord:
                print(f"  {'':<20} {dim('Coords: ' + coord)}")

    input(f"\n  {dim('Enter para continuar...')}")


def _es_privada(ip: str) -> bool:
    import ipaddress
    try:
        return ipaddress.ip_address(ip).is_private
    except Exception:
        return True


# ── 6. Ver reporte ────────────────────────────────────────────────────────

def _ver_reporte():
    from utils.reportes import leer_ultimo_reporte
    separador("Último reporte")
    print(f"\n{leer_ultimo_reporte()}\n")
    input(f"  {dim('Enter para continuar...')}")


# ── 7. Info de interfaces de red ──────────────────────────────────────────

def _info_interfaces():
    import subprocess, platform, socket

    separador("Interfaces de red")
    print()

    sistema = platform.system().lower()
    ip_local = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    hostname = socket.gethostname()
    print(f"  {resaltar('Hostname:')}         {hostname}")
    print(f"  {resaltar('IP local:')}         {ip_local or '—'}")

    try:
        ip_pub_req = __import__("urllib.request", fromlist=["urlopen"]).urlopen(
            "https://api.ipify.org", timeout=5).read().decode()
        print(f"  {resaltar('IP pública:')}       {ip_pub_req}")
    except Exception:
        print(f"  {resaltar('IP pública:')}       {warn('No disponible')}")

    print()
    try:
        if sistema == "windows":
            r = subprocess.run(["ipconfig", "/all"], capture_output=True, text=True, timeout=10)
        else:
            r = subprocess.run(["ip", "addr"], capture_output=True, text=True, timeout=10)
        # Mostrar solo líneas relevantes
        for line in r.stdout.splitlines():
            l = line.strip()
            if any(k in l.lower() for k in ["adapter", "dirección ipv4", "ipv4 address",
                                             "máscara de subred", "subnet mask",
                                             "puerta de enlace", "default gateway",
                                             "inet ", "ether", "descripción", "description",
                                             "dirección física", "physical address"]):
                print(f"  {dim(l)}")
    except Exception as e:
        print(f"  {warn('No se pudo obtener info de interfaces: ' + str(e))}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── 8. Geolocalizar IP manual ─────────────────────────────────────────────

def _geolocalizacion_manual():
    from core.web_service import geolocalizacion_ip

    separador("Geolocalizar IP pública")
    print(f"\n  {dim('Deja vacío para usar tu IP pública actual.')}")
    ip_input = input(f"\n  {info('IP a consultar:')} ").strip()

    if not ip_input:
        try:
            import urllib.request
            ip_input = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
            print(f"  {dim('Tu IP pública: ' + ip_input)}")
        except Exception:
            print(f"  {fallo('No se pudo obtener la IP pública.')}")
            input(f"\n  {dim('Enter para continuar...')}")
            return

    print(f"\n  {info('Consultando ' + ip_input + '...')}\n")
    geo = geolocalizacion_ip(ip_input)

    if geo.get("privada"):
        print(f"  {warn('Es una IP privada/local, no tiene geolocalización.')}")
    elif geo.get("error"):
        print(f"  {fallo('Error: ' + geo['error'])}")
    else:
        separador()
        campos = [
            ("IP",       geo.get("ip",      "—")),
            ("País",     geo.get("pais",    "—") + " (" + geo.get("codigo","?") + ")"),
            ("Región",   geo.get("region",  "—")),
            ("Ciudad",   geo.get("ciudad",  "—")),
            ("ISP",      geo.get("isp",     "—")),
            ("Org",      geo.get("org",     "—")),
            ("AS",       geo.get("as",      "—")),
            ("Coordenadas", str(geo.get("lat","—")) + ", " + str(geo.get("lon","—"))),
        ]
        for label, valor in campos:
            print(f"  {resaltar(label + ':'):<28} {valor}")
        separador()

    input(f"\n  {dim('Enter para continuar...')}")


# ── 9. Configuración rápida ───────────────────────────────────────────────

def _configuracion_rapida():
    separador("Configuración rápida")
    print(f"""
  {info('Archivos de configuración:')}

  {resaltar('config/device.py')}
    → Dispositivos a monitorear (IP, MAC, nombre, grupo)
    → Servicios web personalizados
    → Rango IP para escaneo

  {resaltar('config/smtp_config.py')}
    → Credenciales de correo para alertas automáticas

  {resaltar('config/settings.py')}
    → Intervalo de monitoreo, versión, timeouts, reportes

  {dim('Edita estos archivos con tu editor de texto favorito.')}
  {dim('Luego reinicia Visor para aplicar los cambios.')}
""")
    input(f"  {dim('Enter para volver...')}")


# ── CLI directo (flags) ───────────────────────────────────────────────────

def run_direct(args):
    banner()
    if args.scan:     _escaneo_unico()
    if args.web:      _menu_web()
    if args.internet: _menu_internet()
    if args.report:   _ver_reporte()
