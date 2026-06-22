"""
core/monitor.py — Escaneo de dispositivos configurados en config/device.py
"""

from datetime import datetime
from core.red import hacer_ping, buscar_ip_por_mac, resolver_host
from core.mail import enviar_alerta
from config.device import DISPOSITIVOS
from config.settings import PING_COUNT, PING_TIMEOUT


def _resolver_direccion(dispositivo: dict) -> tuple[str | None, str]:
    """
    Devuelve (ip_resuelta, método).
    Prioridad: MAC → IP → hostname.
    """
    mac = dispositivo.get("mac", "").strip()
    ip  = dispositivo.get("ip", "").strip()

    if mac:
        ip_arp = buscar_ip_por_mac(mac)
        if ip_arp:
            return ip_arp, "ARP"
        # Si no está en ARP, intentar con IP si existe
        if ip:
            return ip, "IP (MAC no encontrada)"
        return None, "MAC no encontrada"

    if ip:
        # Puede ser IP o hostname/dominio
        ip_res = resolver_host(ip)
        if ip_res and ip_res != ip:
            return ip_res, f"DNS ({ip})"
        return ip, "IP directa"

    return None, "Sin dirección"


def escanear_dispositivos(dispositivos: list[dict] | None = None) -> list[dict]:
    """
    Escanea la lista de dispositivos. Si no se pasa ninguna, usa la de config/device.py.
    Devuelve lista de resultados enriquecidos.
    """
    if dispositivos is None:
        dispositivos = DISPOSITIVOS

    resultados = []
    for dev in dispositivos:
        ip, metodo = _resolver_direccion(dev)

        if ip:
            online, lat = hacer_ping(ip, count=PING_COUNT, timeout=PING_TIMEOUT)
        else:
            online, lat = False, None

        resultado = {
            "nombre":   dev.get("nombre", "Sin nombre"),
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


def monitoreo_continuo(intervalo: int = 60, callback=None):
    """
    Monitoreo continuo. Detecta cambios de estado y envía alertas.
    callback(resultados) se llama en cada ciclo si se especifica.
    """
    import time
    from core.colores import ok, fallo, info, dim, separador

    estados_anteriores: dict[str, str] = {}
    ciclo = 0

    while True:
        ciclo += 1
        separador(f"Ciclo {ciclo} — {datetime.now().strftime('%H:%M:%S')}")

        resultados = escanear_dispositivos()
        caidos = []

        for r in resultados:
            nombre = r["nombre"]
            estado = r["estado"]
            anterior = estados_anteriores.get(nombre)

            if estado == "UP":
                print(ok(f"{nombre} ({r['ip']}) — {r['latencia']} ms"))
                if anterior == "DOWN":
                    # Recuperado
                    enviar_alerta(
                        tipo="recuperado",
                        nombre=nombre,
                        ip=r["ip"],
                        detalles=f"Latencia: {r['latencia']} ms"
                    )
            else:
                print(fallo(f"{nombre} ({r['ip']}) — Sin respuesta"))
                caidos.append(nombre)
                if anterior != "DOWN":
                    # Nuevo fallo
                    enviar_alerta(
                        tipo="caida",
                        nombre=nombre,
                        ip=r["ip"],
                        detalles="No responde a ping"
                    )

            estados_anteriores[nombre] = estado

        if callback:
            callback(resultados)

        if caidos:
            caidos_str = ', '.join(caidos)
            print(f"\n  {dim(f'Dispositivos caidos: {len(caidos)} -- {caidos_str}')}")

        print(f"\n  {dim(f'Próximo ciclo en {intervalo}s... (Ctrl+C para salir)')}")
        try:
            time.sleep(intervalo)
        except KeyboardInterrupt:
            print("\n\n  Monitoreo detenido.\n")
            break
