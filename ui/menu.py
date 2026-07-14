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
        print(f"  {resaltar('9.')} 🛡️   Auditoría de Seguridad (Metatron)")
        print(f"  {resaltar('A.')} 🔫  Arsenal de Comandos (Quick Support)")
        print(f"  {resaltar('B.')} 🩺  Diagnóstico de Salud (Jitter/Loss)")
        print(f"  {resaltar('C.')} 🦖  Raptor Eye (Threat Hunting)")
        print(f"  {resaltar('G.')} 🛡️  Guardian AI (Pentest Assistant)")
        print(f"  {resaltar('M.')} 🐍  Medusa Shield (Security Scan)")
        print(f"  {resaltar('I.')} 🖥️  Infraestructura L3 (MikroTik/Proxmox)
  {resaltar('L.')} 🌐  LAN Vision — Descubrimiento de Red
  {resaltar('O.')} 🕹️  Orchestrator (Auto-Pilot)")
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
        elif opcion == "9": _menu_auditoria_seguridad()
        elif opcion.upper() == "A": _menu_arsenal()
        elif opcion.upper() == "B": _menu_salud_red()
        elif opcion.upper() == "C": _menu_raptor_eye()
        elif opcion.upper() == "G": _menu_guardian_ai()
        elif opcion.upper() == "M": _menu_medusa_shield()
        elif opcion.upper() == "O": _menu_orchestrator()
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
            lat_web = s.get("latencia")
            lat_red = s.get("lat_red")
            http   = s.get("http", "—")
            
            # Formato de latencia: [Red -> Web]
            lat_s = f"{lat_web:.0f}ms" if lat_web else "—"
            if lat_red:
                lat_s = f"{lat_red:.0f}ms -> {lat_web:.0f}ms"
            
            color_web = ok if lat_web and lat_web < 400 else warn
            estado = ok("  UP  ") if online else fallo(" DOWN ")
            
            print(f"  {nombre:<{ancho}} [{estado}]  HTTP {http:<4}  {color_web(lat_s)}")

    separador()
    print(f"  TOTAL:  {ok(str(total_up) + '/' + str(total_tot) + ' servicios activos') if total_up == total_tot else warn(str(total_up) + '/' + str(total_tot) + ' servicios activos')}")

    ruta = guardar_reporte({"ts": datetime.now().isoformat(), "web": categorias})
    if ruta:
        print(f"  {dim('Reporte guardado: ' + ruta.name)}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── 4. Test de internet ───────────────────────────────────────────────────

def _menu_internet():
    from core.test_internet import test_internet as medir_calidad
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
    _linea("Jitter:",             f"{jitter} ms"  if jitter is not None else "—",  jitter is not None and jitter < 20)
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
        ip_h  = h.get("host", "")
        # Si no hay latencia pero lats tiene datos, usamos el primero (fallback)
        if lat_h is None and h.get("lats"):
            lat_h = h["lats"][0]
            
        estado_h = ok(f"{lat_h} ms") if lat_h and lat_h < 150 else (warn(f"{lat_h} ms") if lat_h else fallo("Sin respuesta"))
        print(f"  {h.get('nombre',''):<16} {ip_h:<16} {estado_h}")

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


def _menu_auditoria_seguridad():
    from core.security import auditoria_completa
    from utils.database import inicializar_db, guardar_sesion_seguridad, obtener_historial_reciente
    
    inicializar_db()
    separador("🛡️ Auditoría de Seguridad (Motor Metatron)")
    
    # Mostrar historial reciente
    try:
        historial = obtener_historial_reciente(3)
        if historial:
            print(f"  {dim('Historial reciente:')}")
            for h in historial:
                print(f"    {h[1]} | {h[2]} | {h[3]}")
            print()
    except Exception:
        pass

    ip = input(f"  {info('Ingresa la IP o Dominio para auditar:')} ").strip()
    if not ip: return

    print(f"\n  {naranja('Ejecutando escaneo profundo de puertos y servicios...')}")
    print(f"  {dim('Esto puede tardar unos segundos...')}\n")
    
    res = auditoria_completa(ip)
    
    # Mostrar Resultados
    print(f"  Resultado para {resaltar(ip)}:")
    print(f"  Riesgo General:  " + (fallo(res['riesgo_general']) if res['riesgo_general'] in ('ALTO','CRÍTICO') else (warn(res['riesgo_general']) if res['riesgo_general'] == 'MEDIO' else ok(res['riesgo_general']))))
    print(f"  Puertos Abiertos: {res['total_abiertos']}")
    separador()
    
    if res['puertos_abiertos']:
        p_head = azul("PORT")
        s_head = azul("SERVICE")
        r_head = azul("RISK")
        i_head = azul("INFO")
        print(f"  {p_head:<18} {s_head:<22} {r_head:<18} {i_head}")
        for p in res['puertos_abiertos']:
            r_color = fallo if p['riesgo'] in ('ALTO','CRÍTICO') else (warn if p['riesgo'] == 'MEDIO' else ok)
            p_str = str(p['puerto'])
            s_str = p['servicio']
            r_str = r_color(p['riesgo'])
            d_str = dim(p['descripcion'])
            print(f"  {p_str:<8} {s_str:<12} {r_str:<18} {d_str}")
    else:
        print(f"  {ok('No se detectaron puertos abiertos comunes.')}")
    
    # Guardar en DB
    try:
        sesion_id = guardar_sesion_seguridad(ip, res)
        print(f"\n  {dim(f'Auditoría guardada en base de datos local (Sesión ID: {sesion_id})')}")
    except Exception as e:
        print(f"\n  {warn(f'No se pudo guardar en la base de datos: {e}')}")
    
    separador()
    input(f"  {dim('Enter para continuar...')}")


def _menu_arsenal():
    from config.arsenal_commands import ARSENAL_LIBRARY
    from core.arsenal import obtener_placeholders, procesar_comando
    import os

    while True:
        separador("🔫 ARSENAL: Biblioteca de Comandos Rápidos")
        
        # Listar Categorías
        for i, cat in enumerate(ARSENAL_LIBRARY, 1):
            print(f"  {resaltar(str(i)+'.')} {cat['categoria']}")
        print(f"  {resaltar('0.')} Volver")
        
        op_cat = input(f"\n  {info('Selecciona una categoría:')} ").strip()
        if op_cat == "0" or not op_cat: break
        
        try:
            categoria = ARSENAL_LIBRARY[int(op_cat)-1]
            while True:
                separador(f"📁 {categoria['categoria']}")
                for i, cmd in enumerate(categoria['comandos'], 1):
                    print(f"  {resaltar(str(i)+'.')} {cmd['titulo']}")
                    print(f"     {dim(cmd['desc'])}")
                print(f"  {resaltar('0.')} Volver")

                op_cmd = input(f"\n  {info('Selecciona un comando para preparar:')} ").strip()
                if op_cmd == "0" or not op_cmd: break
                
                try:
                    cmd_obj = categoria['comandos'][int(op_cmd)-1]
                    raw_cmd = cmd_obj['cmd']
                    
                    # Pedir valores para placeholders
                    campos = obtener_placeholders(raw_cmd)
                    valores = {}
                    if campos:
                        print(f"\n  {naranja('Configura los parámetros del comando:')}")
                        for c in campos:
                            # Limpiar el nombre si tiene default {{campo|default}}
                            nombre_limpio = c.split("|")[0]
                            default = c.split("|")[1] if "|" in c else ""
                            
                            prompt = f"    {nombre_limpio}"
                            if default: prompt += f" (default: {default})"
                            
                            val = input(f"{prompt}: ").strip()
                            if val: valores[nombre_limpio] = val
                    
                    cmd_final = procesar_comando(raw_cmd, valores)
                    
                    separador("🚀 COMANDO LISTO")
                    print(f"\n  {resaltar(cmd_final)}\n")
                    print(f"  {dim('Copia y pega este comando en tu terminal.')}")
                    
                    # Opción extra: intentar ejecutar (solo si el usuario quiere)
                    ejecutar = input(f"\n  {warn('¿Intentar ejecutar directamente? (s/n):')} ").strip().lower()
                    if ejecutar == 's':
                        print(f"\n  {azul('Ejecutando...')}\n")
                        os.system(cmd_final)
                        input(f"\n  {dim('Presiona Enter para continuar...')}")
                    
                except (ValueError, IndexError):
                    print(f"  {fallo('Opción inválida.')}")
        except (ValueError, IndexError):
            print(f"  {fallo('Categoría inválida.')}")



def _menu_salud_red():
    from core.health import analizar_calidad
    
    separador("🩺 Diagnóstico de Salud de Red")
    target = input(f"  {info('Ingresa IP/Dominio para medir calidad:')} ").strip()
    if not target: return
    
    try:
        cant = int(input(f"  {info('Número de paquetes (default 10):')} ") or 10)
    except: cant = 10
    
    print(f"\n  {naranja('Midiendo estabilidad de la conexión...')}")
    res = analizar_calidad(target, cant)
    
    if res['estado'] == 'ONLINE':
        separador(f"RESULTADOS: {target}")
        
        # Color según calidad
        color_c = ok if res['calidad'] == 'EXCELENTE' else (fallo if res['calidad'] in ('CRÍTICA','INESTABLE') else warn)
        
        print(f"  Calidad General:  {color_c(res['calidad'])}")
        print(f"  Latencia Media:   {resaltar(str(res['avg'])+' ms')}")
        print(f"  Jitter (Varianza): {res['jitter']} ms")
        print(f"  Pérdida (Loss):    {res['loss']}%")
        print(f"  Rango:            {res['min']}ms - {res['max']}ms")
        
        if res['jitter'] > 15:
            print(f"\n  {warn('ALERTA:')} Jitter elevado detectado. Puede afectar Voz sobre IP o Juegos.")
        if res['loss'] > 0:
            print(f"  {fallo('ALERTA:')} Hay pérdida de paquetes. Revisa el cableado o el proveedor (ISP).")
            
    else:
        print(f"  {fallo('ERROR:')} El objetivo no responde a los pings.")
        
    separador()
    input(f"  {dim('Enter para continuar...')}")


def _menu_raptor_eye():
    from core.raptor_eye import hunt_vulnerabilities, scan_network_threats
    from core.red import detectar_gateway
    
    separador("🦖 RAPTOR EYE: Inteligencia de Amenazas")
    print(f"  {dim('Inspirado en RAPTOR AI - Pensamiento Adversario')}\n")
    print(f"  {resaltar('1.')} Escaneo de un Objetivo Único")
    print(f"  {resaltar('2.')} Búsqueda en Red Local (Threat Hunting)")
    print(f"  {resaltar('0.')} Volver")
    
    op = input(f"\n  {info('Selecciona una modalidad:')} ").strip()
    
    if op == "1":
        target = input(f"  {info('IP/Dominio del objetivo:')} ").strip()
        if not target: return
        print(f"\n  {naranja('Cazando vectores de ataque en')} {resaltar(target)}...")
        findings = hunt_vulnerabilities(target)
        
        if findings:
            print(f"\n  {fallo('¡ATENCIÓN!')} Se encontraron vectores críticos:\n")
            for f in findings:
                print(f"  [{fallo(f['risk'])}] Puerto {f['port']}: {f['desc']}")
        else:
            print(f"\n  {ok('No se detectaron vectores de ataque comunes.')}")
            
    elif op == "2":
        gw = detectar_gateway() or "192.168.1.1"
        prefix = ".".join(gw.split(".")[:-1])
        print(f"\n  {naranja('Iniciando cacería en el segmento')} {resaltar(prefix+'.0/24')}...")
        print(f"  {dim('Analizando hosts activos y sus servicios críticos...')}\n")
        
        results = scan_network_threats(prefix)
        
        if results:
            print(f"  {titulo('REPORTE DE AMENAZAS EN RED')}")
            for r in results:
                print(f"\n  {resaltar(r['ip'])}:")
                for t in r['threats']:
                    print(f"    - {t['desc']} ({fallo(t['risk'])})")
        else:
            print(f"\n  {ok('Red limpia. No se encontraron vectores expuestos.')}")

    separador()
    input(f"  {dim('Enter para continuar...')}")


def _menu_guardian_ai():
    from core.raptor_eye import hunt_vulnerabilities
    from core.guardian_ai import generate_remediation_plan
    
    separador("🛡️ GUARDIAN AI: Orquestador de Pentesting")
    print(f"  {dim('IA de Remediación Basada en Flujos - Jasol Group')}\n")
    
    target = input(f"  {info('IP del host para análisis profundo:')} ").strip()
    if not target: return
    
    print(f"\n  {naranja('1. [Raptor] Auditando superficies...')}")
    findings = hunt_vulnerabilities(target)
    
    if not findings:
        print(f"  {ok('No se detectaron vectores críticos. El host parece seguro.')}")
    else:
        print(f"  {fallo('¡Hallazgos detectados!')} Generando hoja de ruta con Guardian AI...\n")
        plan = generate_remediation_plan(findings)
        
        print(f"  {titulo('HOJA DE RUTA DE SEGURIDAD')}")
        for item in plan:
            print(f"\n  {resaltar('●')} {item['vector']} ({fallo(item['risk'])})")
            print(f"    {naranja('Acción:')} {item['remediation']}")
            print(f"    {info('Arsenal recomendado:')} {', '.join(item['suggested_tools'])}")

    separador()
    input(f"  {dim('Enter para continuar...')}")


def _menu_medusa_shield():
    from core.medusa_shield import medusa_full_scan
    
    separador("🐍 MEDUSA SHIELD: Seguridad de Código e Integridad")
    print(f"  {dim('Inspirado en Medusa AI - Escaneo de Secretos y Vetting')}\n")
    
    print(f"  {naranja('Iniciando escaneo profundo en el directorio raíz...')}")
    results = medusa_full_scan()
    
    # Reportar Secretos
    print(f"\n  {titulo('1. ESCANEO DE SECRETOS Y LLAVES')}")
    if results['secrets']:
        for s in results['secrets']:
            print(f"  [{fallo('EXPOSED')}] {s['type']} en {resaltar(os.path.basename(s['file']))} (Línea {s['line']})")
    else:
        print(f"  {ok('No se detectaron secretos o llaves expuestas.')}")
        
    # Reportar Integridad
    print(f"\n  {titulo('2. AUDITORÍA DE INTEGRIDAD DE IA')}")
    for i in results['integrity']:
        color_status = ok if i['status'] == "VERIFIED" else fallo
        print(f"  [{color_status(i['status'])}] Módulo {resaltar(i['module'])}: {i['check']}")

    separador()
    input(f"  {dim('Enter para continuar...')}")


def _menu_orchestrator():
    from core.orchestrator import run_orchestrated_task
    
    separador("🕹️ ORCHESTRATOR: Misión Autónoma (Auto-Pilot)")
    print(f"  {dim('Coordinación de Agentes en Paralelo - Jasol Group')}\n")
    
    target = input(f"  {info('Objetivo de la misión (IP/Dominio o vacío para local):')} ").strip()
    
    print(f"\n  {naranja('Ejecutando misión de auditoría 360°...')}")
    results = run_orchestrated_task("SECURITY_AUDIT", target if target else None)
    
    if results:
        print(f"\n  {ok('Misión completada con éxito.')}")
        print(f"  - Agentes desplegados: Raptor, Medusa, Guardian.")
        
        if 'raptor' in results and results['raptor']:
            print(f"  - {fallo('Hallazgos Raptor:')} {len(results['raptor'])} vulnerabilidades.")
        if 'medusa' in results and results['medusa']:
            print(f"  - {fallo('Alertas Medusa:')} {len(results['medusa'])} secretos detectados.")
        if 'guardian' in results:
            print(f"  - {ok('Guardian:')} Plan de remediación generado automáticamente.")
    
    separador()
    input(f"  {dim('Enter para continuar...')}")


# ── CLI directo (flags) ───────────────────────────────────────────────────

def run_direct(args):
    banner()
    if args.scan:     _escaneo_unico()
    if args.web:      _menu_web()
    if args.internet: _menu_internet()
    if args.report:   _ver_reporte()

def _menu_infraestructura_l3():
    from ui.menu_infraestructura import menu_infraestructura
    menu_infraestructura()

def _menu_lan_vision():
    from ui.menu_lan_vision import menu_lan_vision
    menu_lan_vision()
