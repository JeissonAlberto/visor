"""Consulta manual y de solo lectura de reputación de IPs en AbuseIPDB."""
import http.client
import ipaddress
import json
import os
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://api.abuseipdb.com/api/v2/check"
MAX_RESPONSE = 65536


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def consultar_ip(ip_texto, clave=None):
    """Consulta una IP pública; no envía reportes ni actúa sobre la red."""
    try:
        ip = ipaddress.ip_address(ip_texto.strip())
    except (AttributeError, ValueError):
        return {"ok": False, "error": "IP inválida; introduce una IPv4 o IPv6 pública."}
    if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_loopback or ip.is_link_local or (ip.version == 6 and ip.ipv4_mapped):
        return {"ok": False, "error": "Solo se consultan IP públicas; no se enviaron datos."}
    key = clave if clave is not None else os.environ.get("VISOR_ABUSEIPDB_API_KEY", "")
    if not isinstance(key, str) or not key.strip() or any(c in key for c in "\r\n"):
        return {"ok": False, "error": "Falta configurar VISOR_ABUSEIPDB_API_KEY."}
    query = urllib.parse.urlencode({"ipAddress": str(ip), "maxAgeInDays": 90})
    request = urllib.request.Request(ENDPOINT + "?" + query, headers={"Key": key.strip(), "Accept": "application/json", "User-Agent": "Visor-NOC/5.2"})
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=10) as response:
            body = response.read(MAX_RESPONSE + 1)
        if len(body) > MAX_RESPONSE:
            return {"ok": False, "error": "Respuesta demasiado grande de AbuseIPDB."}
        data = json.loads(body.decode("utf-8"))["data"]
        if not isinstance(data, dict) or ipaddress.ip_address(data.get("ipAddress", "")) != ip:
            raise ValueError("respuesta inválida")
        score, total = data.get("abuseConfidenceScore"), data.get("totalReports")
        if type(score) is not int or not 0 <= score <= 100 or type(total) is not int or total < 0:
            raise ValueError("respuesta inválida")
        def safe_text(value):
            if value is None:
                return None
            if not isinstance(value, str):
                raise ValueError("respuesta inválida")
            return "".join(c for c in value if c.isprintable())[:200]
        return {"ok": True, "ip": str(ip), "score": score, "reports": total,
                "last_reported": safe_text(data.get("lastReportedAt")),
                "country": safe_text(data.get("countryCode")), "isp": safe_text(data.get("isp")),
                "days": 90}
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            message = "Clave rechazada o acceso denegado por AbuseIPDB."
        elif exc.code == 429:
            message = "Límite de consultas de AbuseIPDB alcanzado; consulta la cuota de tu cuenta."
        else:
            message = f"AbuseIPDB devolvió HTTP {exc.code}."
        return {"ok": False, "error": message}
    except (urllib.error.URLError, http.client.HTTPException, OSError, TimeoutError):
        return {"ok": False, "error": "No se pudo conectar con AbuseIPDB."}
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
        return {"ok": False, "error": "Respuesta inválida de AbuseIPDB."}
