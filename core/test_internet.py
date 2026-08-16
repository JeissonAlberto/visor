"""
core/test_internet.py — Test completo de calidad de internet.
Mide latencia, jitter, pérdida, velocidad de descarga, subida y throughput.
Sin dependencias externas — solo stdlib.
"""

import subprocess
import platform
import re
import statistics
import time
import urllib.request
import urllib.error
import socket
import threading
import io
from config.settings import PING_COUNT


HOSTS_REFERENCIA = [
    ("Google DNS",   "8.8.8.8"),
    ("Cloudflare",   "1.1.1.1"),
    ("Google DNS 2", "8.8.4.4"),
]

# Servidores de descarga — múltiples opciones ordenadas por confiabilidad desde Colombia
_DOWNLOAD_URLS = [
    ("Cloudflare",   "https://speed.cloudflare.com/__down?bytes=5000000"),   # 5 MB  — CDN global, excelente desde CO
    ("TELE2 10MB",   "https://speedtest.tele2.net/10MB.bin"),                # 10 MB — servidor EU dedicado
    ("TELE2 1MB",    "https://speedtest.tele2.net/1MB.bin"),                 # 1 MB  — fallback ligero
    ("Hetzner",      "https://speed.hetzner.de/10MB.bin"),                   # 10 MB — servidor DE
    ("OVH",          "https://proof.ovh.net/files/10Mb.dat"),                # 10 MB — servidor FR
]

# Servidores de subida — en orden de preferencia
_UPLOAD_ENDPOINTS = [
    ("Cloudflare",  "https://speed.cloudflare.com/__up",    "POST", 2_000_000),   # 2 MB
    ("httpbin.org", "https://httpbin.org/post",             "POST", 1_000_000),   # 1 MB fallback
    ("postman-echo","https://postman-echo.com/post",        "POST", 1_000_000),   # 1 MB fallback
]
_UPLOAD_SIZE = 2_000_000   # default 2 MB


# ── Latencia ──────────────────────────────────────────────────────────────

def _ping_latencias(host: str, count: int = 4) -> list[float]:
    """Devuelve lista de latencias individuales en ms."""
    sistema = platform.system().lower()
    if sistema == "windows":
        # -n paquetes, -w espera (ms)
        cmd = ["ping", "-n", str(count), "-w", "1000", host]
    else:
        cmd = ["ping", "-c", str(count), "-W", "1", host]

    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=count * 2 + 2)
        salida = r.stdout
        # Regex compatible con Windows (español/inglés) y Linux
        lats = re.findall(r"(?:tiempo|time)[=<]([\d.]+)\s*ms", salida, re.IGNORECASE)
        
        # Fallback para formatos sin 'ms' o separadores diferentes
        if not lats:
            lats = re.findall(r"(?:tiempo|time)[=<]([\d.]+)", salida, re.IGNORECASE)

        valores = []
        for v in lats:
            try:
                val = float(v)
                if val >= 0: valores.append(val)
            except ValueError:
                pass
        
        # Fallback final: buscar estadísticas si no hay individuales
        if not valores:
            m = re.search(r"(?:Media|Average) = ([\d.]+)ms", salida, re.IGNORECASE)
            if m:
                return [float(m.group(1))] * count
                
        return valores
    except Exception:
        return []


# ── Velocidad de descarga ─────────────────────────────────────────────────

def _medir_descarga(duracion_max: float = 8.0) -> tuple[float | None, str]:
    """
    Descarga datos de un servidor público y mide Mbps.
    Devuelve (mbps, fuente) o (None, motivo_error).
    """
    ctx = _ssl_ctx()

    for nombre, url in _DOWNLOAD_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Visor-NOC/2.0"})
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
                descargado = 0
                chunk = 65536
                while True:
                    if time.perf_counter() - t0 >= duracion_max:
                        break
                    bloque = resp.read(chunk)
                    if not bloque:
                        break
                    descargado += len(bloque)

            elapsed = time.perf_counter() - t0
            if elapsed > 0.5 and descargado > 0:
                mbps = round((descargado * 8) / elapsed / 1_000_000, 2)
                return mbps, nombre
        except Exception:
            continue

    return None, "Sin acceso a servidores de prueba"


# ── Velocidad con speedtest-cli (nativo) ─────────────────────────────────

def _medir_con_speedtest() -> tuple[float | None, float | None, str]:
    """
    Usa speedtest-cli si está instalado.
    Devuelve (descarga_mbps, subida_mbps, fuente) o (None, None, motivo).
    """
    import subprocess, json as _json, shutil
    exe = shutil.which("speedtest") or shutil.which("speedtest-cli")
    if not exe:
        return None, None, "speedtest-cli no instalado"
    try:
        r = subprocess.run(
            [exe, "--json", "--timeout", "30"],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode != 0:
            return None, None, "speedtest error"
        data  = _json.loads(r.stdout)
        dl    = round(data["download"] / 1_000_000, 2)
        ul    = round(data["upload"]   / 1_000_000, 2)
        server = data.get("server", {}).get("name", "Speedtest.net")
        return dl, ul, server
    except Exception as e:
        return None, None, str(e)


def _medir_subida(duracion_max: float = 10.0) -> tuple[float | None, str]:
    """
    Sube datos a varios servidores en orden y mide Mbps.
    Devuelve (mbps, fuente) o (None, motivo_error).
    """
    ctx = _ssl_ctx()

    for nombre, url, method, size in _UPLOAD_ENDPOINTS:
        datos = b"X" * size
        try:
            req = urllib.request.Request(
                url,
                data=datos,
                method=method,
                headers={
                    "Content-Type":   "application/octet-stream",
                    "User-Agent":     "Visor-NOC/2.0",
                    "Content-Length": str(len(datos)),
                }
            )
            t0 = time.perf_counter()
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                resp.read()
            elapsed = time.perf_counter() - t0

            if elapsed > 0.2:
                mbps = round((len(datos) * 8) / elapsed / 1_000_000, 2)
                return mbps, nombre
        except Exception:
            continue

    return None, "Sin acceso al servidor de subida"


# ── Throughput TCP local ──────────────────────────────────────────────────

def _medir_throughput_tcp() -> tuple[float | None, str]:
    """
    Mide throughput TCP local (loopback) en Mbps.
    Indica la capacidad del stack de red del sistema.

    El servidor usa un puerto efímero para evitar colisiones con otros
    procesos y para no enviar datos accidentalmente a un servicio que ya
    estuviera escuchando en un puerto fijo.
    """
    DATOS = 10 * 1024 * 1024   # 10 MB
    estado = {"puerto": None, "error": None}
    servidor_listo = threading.Event()

    def servidor():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(("127.0.0.1", 0))
                srv.listen(1)
                srv.settimeout(5)
                estado["puerto"] = srv.getsockname()[1]
                servidor_listo.set()
                conn, _ = srv.accept()
                with conn:
                    recibido = 0
                    while recibido < DATOS:
                        bloque = conn.recv(65536)
                        if not bloque:
                            break
                        recibido += len(bloque)
        except Exception as e:
            estado["error"] = str(e)
            servidor_listo.set()

    hilo = threading.Thread(target=servidor, daemon=True)
    hilo.start()
    if not servidor_listo.wait(timeout=5):
        return None, "El servidor loopback no estuvo disponible"
    if estado["error"] or estado["puerto"] is None:
        return None, estado["error"] or "No se pudo abrir el servidor loopback"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cli:
            cli.settimeout(5)
            cli.connect(("127.0.0.1", estado["puerto"]))
            chunk = b"X" * 65536
            enviado = 0
            t0 = time.perf_counter()
            while enviado < DATOS:
                n = cli.send(chunk[:min(len(chunk), DATOS - enviado)])
                if n <= 0:
                    return None, "El socket loopback no aceptó datos"
                enviado += n
            elapsed = time.perf_counter() - t0

        hilo.join(timeout=5)
        if elapsed > 0:
            mbps = round((DATOS * 8) / elapsed / 1_000_000, 1)
            return mbps, "loopback"
    except Exception as e:
        return None, str(e)
    finally:
        if hilo.is_alive():
            hilo.join(timeout=1)

    return None, "Error desconocido"


# ── SSL helper ────────────────────────────────────────────────────────────

def _ssl_ctx():
    """Crea el contexto HTTPS seguro para las mediciones de velocidad.

    Las fuentes de prueba son externas y no deben convertir el diagnóstico en
    un cliente TLS vulnerable a MITM. Si una fuente tiene un certificado
    inválido, la medición la descarta y continúa con el siguiente fallback.
    """
    import ssl
    return ssl.create_default_context()


# ── Test completo ─────────────────────────────────────────────────────────

def test_internet(count: int | None = None) -> dict:
    """
    Test completo: latencia + jitter + pérdida + descarga + subida + throughput.
    """
    if count is None:
        count = PING_COUNT

    # 1. Latencia y pérdida
    todas_lats = []
    resultados_hosts = []

    for nombre, host in HOSTS_REFERENCIA:
        lats = _ping_latencias(host, count=count)
        perdidos = max(0, count - len(lats))
        avg_h = round(statistics.mean(lats), 1) if lats else None
        
        resultados_hosts.append({
            "host":     host,
            "nombre":   nombre,
            "lats":     lats,
            "latencia": avg_h,
            "perdidos": perdidos,
        })
        todas_lats.extend(lats)

    total_pings    = count * len(HOSTS_REFERENCIA)
    total_perdidos = sum(r["perdidos"] for r in resultados_hosts)
    tasa_perdida   = round((total_perdidos / total_pings) * 100, 1) if total_pings else 100.0

    if todas_lats:
        lat_avg = round(statistics.mean(todas_lats), 1)
        lat_min = round(min(todas_lats), 1)
        lat_max = round(max(todas_lats), 1)
        jitter  = round(statistics.stdev(todas_lats), 1) if len(todas_lats) > 1 else 0.0
    else:
        lat_avg = lat_min = lat_max = jitter = None

    # 2. Velocidad — intentar speedtest-cli primero, luego HTTP
    mbps_dl_st, mbps_ul_st, fuente_st = _medir_con_speedtest()
    if mbps_dl_st is not None:
        mbps_dl,  fuente_dl = mbps_dl_st, fuente_st
        mbps_ul,  fuente_ul = mbps_ul_st, fuente_st
    else:
        mbps_dl, fuente_dl = _medir_descarga()
        mbps_ul, fuente_ul = _medir_subida()

    # 4. Throughput TCP local
    mbps_tp, fuente_tp = _medir_throughput_tcp()

    # 5. Calificación
    calidad = _calificar(lat_avg, tasa_perdida, jitter, mbps_dl)

    return {
        # Latencia
        "lat_avg":       lat_avg,
        "lat_min":       lat_min,
        "lat_max":       lat_max,
        "jitter":        jitter,
        # Pérdida
        "perdida":       tasa_perdida,
        "total_pings":   total_pings,
        "pings_ok":      total_pings - total_perdidos,
        # Velocidades
        "descarga_mbps": mbps_dl,
        "subida_mbps":   mbps_ul,
        "throughput_mbps": mbps_tp,
        "fuente_dl":     fuente_dl,
        "fuente_ul":     fuente_ul,
        "fuente_tp":     fuente_tp,
        # Calidad
        "calidad":       calidad,
        "hosts":         resultados_hosts,
        "ts":            __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }


def _calificar(avg, perdida, jitter, mbps_dl=None):
    if avg is None or perdida >= 80:
        return "SIN CONEXION"
    if perdida > 30 or (avg and avg > 500):
        return "MUY MALA"
    if perdida > 10 or (avg and avg > 200) or (jitter and jitter > 50):
        return "MALA"
    if perdida > 5  or (avg and avg > 100) or (jitter and jitter > 20):
        return "REGULAR"
    if perdida > 0  or (avg and avg > 50)  or (jitter and jitter > 10):
        return "BUENA"
    return "EXCELENTE"
