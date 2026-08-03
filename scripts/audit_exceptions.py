#!/usr/bin/env python3
"""Audita capturas de excepciones demasiado amplias sin modificar el código.

Uso:
    python scripts/audit_exceptions.py
    python scripts/audit_exceptions.py --root . --strict
    python scripts/audit_exceptions.py --json > reports/exception_audit.json

El script identifica ``except:`` y capturas directas de ``Exception`` o
``BaseException``. No reescribe archivos automáticamente: elegir la excepción
correcta requiere revisar la operación que puede fallar.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_EXCLUDED = {".git", ".venv", "venv", "__pycache__", "build", "dist"}
BROAD_NAMES = {"Exception", "BaseException"}


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    column: int
    kind: str
    exception: str
    source: str
    recommendation: str


def _exception_name(node: ast.expr | None) -> str:
    if node is None:
        return "bare except"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_exception_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Tuple):
        return "(" + ", ".join(_exception_name(item) for item in node.elts) + ")"
    return ast.unparse(node)


def _is_broad(node: ast.expr | None) -> bool:
    if node is None:
        return True
    if isinstance(node, ast.Name):
        return node.id in BROAD_NAMES
    if isinstance(node, ast.Tuple):
        return any(_is_broad(item) for item in node.elts)
    return False


def _recommendation(kind: str, exception: str) -> str:
    if kind == "bare_except":
        return "Reemplazar por la excepción concreta esperada; no ocultar KeyboardInterrupt/SystemExit."
    if exception == "BaseException":
        return "Evitar BaseException; capturar una excepción concreta salvo un límite de proceso muy justificado."
    return "Reemplazar Exception por las excepciones concretas que la operación puede producir."


def scan_file(path: Path, root: Path) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    lines = text.splitlines()
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or not _is_broad(node.type):
            continue
        exception = _exception_name(node.type)
        kind = "bare_except" if node.type is None else "broad_except"
        source = lines[node.lineno - 1].strip() if 0 < node.lineno <= len(lines) else ""
        findings.append(Finding(
            file=str(path.relative_to(root)),
            line=node.lineno,
            column=node.col_offset + 1,
            kind=kind,
            exception=exception,
            source=source,
            recommendation=_recommendation(kind, exception),
        ))
    return findings


def iter_python_files(root: Path, excluded: set[str]):
    for path in sorted(root.rglob("*.py")):
        if any(part in excluded for part in path.parts):
            continue
        yield path


def scan(root: Path, excluded: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_python_files(root, excluded):
        findings.extend(scan_file(path, root))
    return findings


def build_report(root: Path, findings: list[Finding]) -> dict:
    return {
        "raiz": str(root),
        "total": len(findings),
        "por_tipo": dict(Counter(item.kind for item in findings)),
        "hallazgos": [asdict(item) for item in findings],
    }


def print_report(report: dict) -> None:
    print(f"Auditoría de excepciones: {report['total']} hallazgo(s)")
    if not report["hallazgos"]:
        print("No se encontraron capturas amplias.")
        return
    for item in report["hallazgos"]:
        print(f"[{item['kind']}] {item['file']}:{item['line']}:{item['column']} — {item['exception']}")
        print(f"  {item['source']}")
        print(f"  Sugerencia: {item['recommendation']}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Raíz del repositorio a auditar")
    parser.add_argument("--json", action="store_true", help="Imprime el resultado como JSON")
    parser.add_argument("--strict", action="store_true", help="Devuelve código 1 si encuentra hallazgos")
    parser.add_argument("--exclude", action="append", default=[], help="Directorio adicional a excluir; puede repetirse")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(f"La raíz no existe o no es un directorio: {root}", file=sys.stderr)
        return 2
    findings = scan(root, DEFAULT_EXCLUDED | set(args.exclude))
    report = build_report(root, findings)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
