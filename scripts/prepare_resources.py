"""Descarga los recursos originales de GitHub antes de desplegar (opcional)."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.resources import MANIFEST, ensure_resource
for relative in MANIFEST:
    try:
        path = ensure_resource(relative)
        print(f"OK: {path} ({path.stat().st_size:,} bytes)")
    except Exception as exc:
        print(f"ERROR: {relative}: {exc}", file=sys.stderr)
        sys.exit(1)
