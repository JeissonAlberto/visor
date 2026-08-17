"""Esquema y adaptador HTTP opcional para la telemetría de Visor.

La salida está desactivada por defecto. No envía nada si el usuario no activa
VISOR_TELEMETRY_ENABLED=1 y configura VISOR_TELEMETRY_URL.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

SCHEMA = "visor.telemetry.v1"
_EVENT_TYPE = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,80}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _identifier(value: Any, include_identifiers: bool) -> str:
    text = str(value or "")
    if include_identifiers:
        return text
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if text else ""


def create_event(event_type: str, payload: dict[str, Any], source: str = "visor",
                 observed_at: str | None = None) -> dict[str, Any]:
    """Crea un evento versionado, independiente del destino de almacenamiento."""
    if not _EVENT_TYPE.fullmatch(event_type):
        raise ValueError("event_type inválido")
    if not isinstance(payload, dict):
        raise TypeError("payload debe ser un objeto")
    return {
        "schema": SCHEMA,
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "source": source,
        "observed_at": observed_at or _utc_now(),
        "payload": payload,
    }


def topology_event(topology: dict[str, Any], include_identifiers: bool = False) -> dict[str, Any]:
    """Convierte una muestra de topología en un evento sin secretos.

    Por defecto anonimiza IP/host de destino. Se puede habilitar la inclusión
    de identificadores solo en una instalación controlada del NOC.
    """
    monitor = topology.get("monitorizacion", {})
    path_metrics = []
    for metric in monitor.get("saltos", []):
        item = {
            "perdida_pct": metric.get("perdida_pct"),
            "promedio_ms": metric.get("promedio_ms"),
            "alcanzable": metric.get("alcanzable"),
        }
        host = metric.get("host")
        if host:
            item["host" if include_identifiers else "host_id"] = _identifier(host, include_identifiers)
        path_metrics.append(item)
    payload = {
        "topology_ts": topology.get("ts"),
        "objetivo_id": _identifier(monitor.get("objetivo"), include_identifiers),
        "resumen": topology.get("resumen", {}),
        "path_metrics": path_metrics,
    }
    return create_event("topology.path_sample", payload, observed_at=topology.get("ts"))


def _endpoint_allowed(url: str) -> bool:
    """Valida el esquema y host antes de enviar telemetría.

    HTTPS se permite para endpoints de ingestión configurados por el usuario.
    HTTP queda limitado a adaptadores locales exactos; usar ``startswith``
    permitiría destinos como ``localhost.evil.example``.
    """
    try:
        parsed = urlsplit(url)
        # No aceptar credenciales embebidas: podrían terminar expuestas en
        # diagnósticos, logs o proxies intermediarios.
        if not parsed.hostname or parsed.username or parsed.password:
            return False
        # Fuerza el parseo del puerto para rechazar URLs malformadas.
        parsed.port
    except ValueError:
        return False

    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower().rstrip(".")
    if scheme == "https":
        return True
    return scheme == "http" and hostname in {"localhost", "127.0.0.1", "::1"}


class TelemetryClient:
    """Cliente stdlib, opt-in, para un endpoint HTTP compatible con ingestión JSON."""

    def __init__(self, url: str | None = None, token: str | None = None,
                 timeout: float = 5.0, enabled: bool | None = None) -> None:
        self.url = (url if url is not None else os.getenv("VISOR_TELEMETRY_URL", "")).strip()
        self.token = token if token is not None else os.getenv("VISOR_TELEMETRY_TOKEN", "")
        self.timeout = max(0.5, min(float(timeout), 30.0))
        self.enabled = enabled if enabled is not None else os.getenv("VISOR_TELEMETRY_ENABLED", "0") == "1"

    def send_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Envía un evento solo con opt-in explícito; nunca devuelve el token."""
        if not self.enabled or not self.url:
            return {"sent": False, "skipped": True, "reason": "telemetría no activada"}
        if not _endpoint_allowed(self.url):
            return {"sent": False, "skipped": True, "reason": "endpoint no permitido para prueba segura"}
        body = json.dumps(event, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "User-Agent": "visor-telemetry/1"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=self.timeout) as response:
                return {"sent": True, "status": int(response.status)}
        except urllib.error.HTTPError as exc:
            return {"sent": False, "status": int(exc.code), "error": "endpoint rechazó el evento"}
        except (urllib.error.URLError, TimeoutError):
            return {"sent": False, "error": "endpoint no disponible o agotó el tiempo"}

    def send_topology(self, topology: dict[str, Any], include_identifiers: bool = False) -> dict[str, Any]:
        return self.send_event(topology_event(topology, include_identifiers=include_identifiers))
