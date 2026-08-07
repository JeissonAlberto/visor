"""Receptor HTTP local para probar la telemetría de Visor sin Jitsu.

Uso:
    python scripts/telemetry_test_adapter.py --port 3049 --once
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class TelemetryHandler(BaseHTTPRequestHandler):
    output_path: Path = Path("reports/telemetry_test_events.jsonl")
    stop_after_one = False
    server_ref: ThreadingHTTPServer | None = None

    def do_POST(self) -> None:  # noqa: N802 - API requerida por http.server
        if self.path != "/events":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            event = json.loads(self.rfile.read(length))
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_error(400, "JSON inválido")
            return
        if not isinstance(event, dict) or event.get("schema") != "visor.telemetry.v1":
            self.send_error(400, "esquema no soportado")
            return
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"accepted":true}\n')
        print(f"Evento recibido: {event.get('event_type', 'desconocido')}")
        if self.stop_after_one and self.server_ref is not None:
            self.server_ref.shutdown()

    def log_message(self, *_args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Receptor local de prueba para eventos de Visor")
    parser.add_argument("--host", default="127.0.0.1", help="Solo se recomienda localhost")
    parser.add_argument("--port", type=int, default=3049)
    parser.add_argument("--once", action="store_true", help="Detenerse después del primer evento válido")
    parser.add_argument("--output", default="reports/telemetry_test_events.jsonl")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        parser.error("el adaptador de prueba solo admite localhost")
    server = ThreadingHTTPServer((args.host, args.port), TelemetryHandler)
    TelemetryHandler.output_path = Path(args.output)
    TelemetryHandler.stop_after_one = args.once
    TelemetryHandler.server_ref = server
    print(f"Adaptador local activo en http://{args.host}:{args.port}/events | Ctrl+C para detener")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAdaptador detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
