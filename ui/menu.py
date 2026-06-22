"""
ui/menu.py — Menú principal de Visor.
"""

from datetime import datetime
from core.colores import banner, separador, titulo, info, ok, fallo, warn, dim, resaltar, tabla_estado
from config.settings import INTERVALO_MONITOREO


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
        print(f"  {resaltar('7.')} ⚙️   Configuración rápida")
        print(f"  {resaltar('0.')} ❌  Salir")
        separador()

        opcion = input(f"\n  {info('Elige una opción:')} ").strip()

        if opcion == "1":
            _menu_monitoreo()
        elif opcion == "2":
            _escaneo_unico()
        elif opcion == "3":
            _menu_web()
        elif opcion == "4":
            _menu_internet()
        elif opcion == "5":
            _menu_rango()
        elif opcion == "6":
            _ver_reporte()
        elif opcion == "7":
            _configuracion_rapida()
        elif opcion == "0":
            print(f"\n  {dim('Creado por Ing. Jeisson Alberto Sarmiento  ·  Jasol Group  ·  Saravena, Arauca, Colombia')}\n")
            break
        else:
            print(f"\n  {warn('Opción inválida. Intenta de nuevo.')}")


# ── Monitoreo continuo ────────────────────────────────────────────────────

def _menu_monitoreo():
    from core.monitor import monitoreo_continuo
    from core.colores import banner
    banner()
    separador("Monitoreo continuo")
    print(f"\n  {info(f'Intervalo: {INTERVALO_MONITOREO}s   ·   Ctrl+C para detener')}\n")
    try:
        monitoreo_continuo(intervalo=INTERVALO_MONITOREO)
    except KeyboardInterrupt:
        pass


# ── Escaneo único ─────────────────────────────────────────────────────────

def _escaneo_unico():
    from core.monitor import escanear_dispositivos
    from utils.reportes import guardar_reporte

    separador("Escaneo de dispositivos")
    print(f"\n  {info('Escaneando...')}\n")

    resultados = escanear_dispositivos()

    up   = [r for r in resultados if r["online"]]
    down = [r for r in resultados if not r["online"]]

    tabla_estado(resultados)
    separador()
    print(f"  {ok(f'{len(up)} en línea')}   {fallo(f'{len(down)} caídos')}   {dim(f'Total: {len(resultados)}')}")

    # Guardar reporte
    ruta = guardar_reporte({
        "ts":          datetime.now().isoformat(),
        "dispositivos": resultados,
    })
    if ruta:
        print(f"\n  {dim(f'Reporte guardado: {ruta.name}')}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── Web ───────────────────────────────────────────────────────────────────

def _menu_web():
    from core.web_service import escanear_por_categorias
    from utils.reportes import guardar_reporte

    separador("Verificar servicios web")
    print(f"\n  {info('Verificando DNS, redes sociales, IAs y tus servicios...')}")
    print(f"  {dim('Puede tardar 15-30 segundos')}\n")

    categorias = escanear_por_categorias()

    total_up  = 0
    total_all = 0

    for cat, resultados in categorias.items():
        if not resultados:
            continue

        up  = sum(1 for r in resultados if r.get("online"))
        tot = len(resultados)
        total_up  += up
        total_all += tot

        color_cat = ok if up == tot else (warn if up > 0 else fallo)
        separador(f"{cat}  {color_cat(str(up)+'/'+str(tot))}")

        ancho = max((len(r.get("nombre", "")) for r in resultados), default=12) + 1

        for r in resultados:
            estado_s = ok("  UP  ") if r.get("online") else fallo(" DOWN ")
            http_s   = str(r.get("http") or "—").rjust(4)
            lat      = r.get("latencia")
            lat_s    = (ok(str(lat)+" ms") if lat and lat < 300 else
                        warn(str(lat)+" ms") if lat and lat < 800 else
                        fallo(str(lat)+" ms") if lat else dim("—")).rjust(10)
            nombre   = r.get("nombre", "")
            print(f"  {nombre:<{ancho}}  [{estado_s}]  HTTP {http_s}  {lat_s}")

    separador()
    color_total = ok if total_up == total_all else (warn if total_up > total_all // 2 else fallo)
    print(f"  {resaltar('TOTAL:')}  {color_total(str(total_up)+'/'+str(total_all)+' servicios activos')}")

    ruta = guardar_reporte({"ts": datetime.now().isoformat(), "web": categorias})
    if ruta:
        print(f"  {dim('Reporte: ' + ruta.name)}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── Internet ──────────────────────────────────────────────────────────────

def _menu_internet():
    from core.test_internet import test_internet
    from utils.reportes import guardar_reporte

    separador("Test de calidad de internet")
    print(f"\n  {info('Midiendo latencia, velocidad y throughput...')}")
    print(f"  {dim('(Esto puede tardar 20-30 segundos)')}\n")

    r = test_internet()

    calidad   = r["calidad"]
    color_cal = ok if calidad in ("EXCELENTE", "BUENA") else (warn if calidad == "REGULAR" else fallo)

    def _mbps(val, fuente=""):
        if val is None:
            return fallo("No disponible")
        color = ok if val >= 10 else (warn if val >= 2 else fallo)
        s = color(f"{val} Mbps")
        if fuente:
            s += f"  {dim('via ' + fuente)}"
        return s

    def _ms(val):
        if val is None:
            return dim("—")
        color = ok if val < 50 else (warn if val < 150 else fallo)
        return color(f"{val} ms")

    separador()
    print(f"  {'Calidad:':<26} {color_cal(calidad)}")
    separador()

    # ── Latencia ──
    print(f"\n  {resaltar('LATENCIA')}")
    print(f"  {'Promedio:':<26} {_ms(r['lat_avg'])}")
    print(f"  {'Mínima:':<26} {_ms(r['lat_min'])}")
    print(f"  {'Máxima:':<26} {_ms(r['lat_max'])}")
    print(f"  {'Jitter:':<26} {_ms(r['jitter'])}")
    print(f"  {'Pérdida de paquetes:':<26} {warn(str(r['perdida'])+'%') if r['perdida'] > 0 else ok('0%')}")
    print(f"  {'Pings OK / Total:':<26} {dim(str(r['pings_ok']) + ' / ' + str(r['total_pings']))}")

    # ── Velocidad ──
    print(f"\n  {resaltar('VELOCIDAD')}")
    print(f"  {'Descarga:':<26} {_mbps(r.get('descarga_mbps'), r.get('fuente_dl',''))}")
    print(f"  {'Subida:':<26} {_mbps(r.get('subida_mbps'), r.get('fuente_ul',''))}")

    # ── Throughput ──
    print(f"\n  {resaltar('THROUGHPUT TCP LOCAL')}")
    tp = r.get("throughput_mbps")
    if tp:
        color_tp = ok if tp >= 500 else (warn if tp >= 100 else fallo)
        print(f"  {'Stack de red:':<26} {color_tp(str(tp) + ' Mbps')}  {dim('(loopback)')}")
    else:
        print(f"  {'Stack de red:':<26} {fallo('No disponible')}")

    # ── Por host ──
    separador()
    print(f"  {resaltar('HOSTS DE REFERENCIA')}")
    for h in r.get("hosts", []):
        lats = h.get("lats", [])
        avg  = round(sum(lats) / len(lats), 1) if lats else None
        s    = ok(f"{avg} ms") if lats else fallo("Sin respuesta")
        perdidos = h.get("perdidos", 0)
        p_str = f"  {dim(str(perdidos) + ' perdido(s)')}" if perdidos else ""
        print(f"  {h['nombre']:<16} {dim(h['host']):<16} {s}{p_str}")

    separador()
    ruta = guardar_reporte({"ts": datetime.now().isoformat(), "internet": r})
    if ruta:
        print(f"  {dim('Reporte guardado: ' + ruta.name)}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── Escaneo de rango ──────────────────────────────────────────────────────

def _menu_rango():
    from core.red import escanear_rango
    from core.web_service import geolocalizacion_ip
    from config.device import RANGO_SCAN

    separador("Escanear rango IP")
    print(f"\n  {info(f'Rango configurado: {RANGO_SCAN}')}")
    rango = input(f"  Introduce el rango CIDR (Enter = {RANGO_SCAN}): ").strip() or RANGO_SCAN

    print(f"\n  {info(f'Escaneando {rango}...')}\n")
    resultados = escanear_rango(rango)
    activos = [r for r in resultados if r["activo"]]

    if not activos:
        print(f"  {warn('No se encontraron hosts activos en el rango.')}")
        input(f"\n  {dim('Enter para continuar...')}")
        return

    # Mostrar hosts activos
    print(f"  {'IP':<18} {'LATENCIA':>10}  HOSTNAME")
    print(f"  {'─'*55}")
    for r in activos:
        lat_s = f"{r['latencia']} ms" if r.get('latencia') else "—"
        host  = r.get("hostname") or ""
        print(f"  {ok(r['ip']):<28} {lat_s:>10}  {dim(host)}")

    print(f"\n  {resaltar(str(len(activos)) + ' host(s) activos de ' + str(len(resultados)) + ' IPs escaneadas')}")

    # Geolocalización
    geo_input = input(f"\n  {info('¿Geolocalizar IPs activas? (s/N): ')}").strip().lower()
    if geo_input in ("s", "si", "sí", "y", "yes"):
        # Filtrar IPs públicas (privadas se saltan solas dentro de geolocalizacion_ip)
        ips = [r["ip"] for r in activos]
        print(f"\n  {info(f'Geolocalizando {len(ips)} IP(s)...')}\n")

        print(f"  {'IP':<18} {'PAÍS':<20} {'CIUDAD':<18} {'ISP':<30}")
        print(f"  {'─'*88}")

        for ip in ips:
            geo = geolocalizacion_ip(ip)
            if geo.get("privada"):
                print(f"  {ip:<18} {dim('IP privada — red local'):<68}")
            elif geo.get("error"):
                print(f"  {ip:<18} {fallo('Sin datos'):<68}")
            else:
                pais   = (geo.get("pais", "?") + " " + geo.get("codigo", ""))[:19]
                ciudad = geo.get("ciudad", "?")[:17]
                isp    = geo.get("isp", "?")[:29]
                lat    = geo.get("lat", "")
                lon    = geo.get("lon", "")
                coord  = f"({lat}, {lon})" if lat and lon else ""
                print(f"  {ip:<18} {pais:<20} {ciudad:<18} {isp:<30}")
                if coord:
                    print(f"  {'':<18} {dim('Coords: ' + coord)}")

    input(f"\n  {dim('Enter para continuar...')}")


# ── Reporte ───────────────────────────────────────────────────────────────

def _ver_reporte():
    from utils.reportes import leer_ultimo_reporte
    separador("Último reporte")
    print(f"\n{leer_ultimo_reporte()}\n")
    input(f"  {dim('Enter para continuar...')}")


# ── Config rápida ─────────────────────────────────────────────────────────

def _configuracion_rapida():
    separador("Configuración rápida")
    print(f"""
  {info('Archivos de configuración:')}

  {resaltar('config/device.py')}
    → Lista de dispositivos a monitorear (IP, MAC, nombre, grupo)
    → Servicios web a verificar
    → Rango IP para escaneo automático

  {resaltar('config/smtp_config.py')}
    → Credenciales de correo para alertas automáticas

  {resaltar('config/settings.py')}
    → Intervalo de monitoreo, timeouts, reportes

  {dim('Edita estos archivos con tu editor de texto favorito.')}
""")
    input(f"  {dim('Enter para volver...')}")


# ── Ejecución directa (flags CLI) ────────────────────────────────────────

def run_direct(args):
    banner()
    if args.scan:
        _escaneo_unico()
    if args.web:
        _menu_web()
    if args.internet:
        _menu_internet()
    if args.report:
        _ver_reporte()
