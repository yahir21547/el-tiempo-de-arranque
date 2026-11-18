"""Recursos incluidos en repositorio fuente, con descarga automática en Streamlit Cloud.

Los archivos originales no se alteran ni se convierten. Al clonar la aplicación,
la descarga inicial evita exigir que el usuario cargue manualmente el Excel.
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import quote
import os
import uuid
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = "yahir21547/el-verdadero-calculo-de-timepo-de-aranque"
BASE = f"https://raw.githubusercontent.com/{SOURCE_REPO}/main/"
EXCEL_NAME = "PMD NEMA V46 ADAPTED APPLICACION V1.xlsx"
MANIFEST = {
    "data/" + EXCEL_NAME: EXCEL_NAME,
    "assets/logo.png": "logo.png",
    "assets/motor_header.png": "motor_header.png",
    "assets/fondo_motor.png": "fondo_motor.png",
}


def location(relative: str) -> Path:
    return ROOT / relative


def ensure_resource(local: str) -> Path:
    path = location(local)
    if path.is_file() and path.stat().st_size > 10:
        return path
    if local not in MANIFEST:
        raise ValueError(f"Recurso desconocido: {local}")
    path.parent.mkdir(parents=True, exist_ok=True)
    source = BASE + quote(MANIFEST[local])
    try:
        resp = requests.get(source, timeout=35, headers={"User-Agent": "MotorStartUp-Streamlit/1.0"})
        resp.raise_for_status()
        if len(resp.content) < 1000:
            raise ValueError("El archivo descargado está incompleto.")
        suffix = path.suffix.lower()
        if suffix == ".xlsx" and resp.content[:2] != b"PK":
            raise ValueError("El archivo obtenido no es un XLSX válido.")
        if suffix == ".png" and resp.content[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("El recurso no es un PNG válido.")
        tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".part")
        try:
            tmp.write_bytes(resp.content)
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                tmp.unlink()
        return path
    except Exception as exc:
        raise RuntimeError(f"No fue posible obtener {MANIFEST[local]} desde GitHub: {exc}. "
                           "Puede copiar el archivo a " + str(path)) from exc


def optional_resource(relative: str) -> Path | None:
    """Devuelve un recurso decorativo local, sin bloquear la UI descargándolo."""
    if relative not in MANIFEST:
        return None
    path = location(relative)
    try:
        return path if path.is_file() and path.stat().st_size > 10 else None
    except OSError:
        return None


def public_resource_url(relative: str) -> str:
    """URL pública para imágenes, cargada por el navegador, no por Python."""
    if relative not in MANIFEST:
        raise ValueError(f"Recurso desconocido: {relative}")
    return BASE + quote(MANIFEST[relative])
