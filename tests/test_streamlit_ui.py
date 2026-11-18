"""Smoke test: la portada debe navegar al formulario sin descargar Excel."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_open_calculator_without_loading_workbook():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "streamlit_app.py"), default_timeout=40)
    app.run()
    assert len(app.exception) == 0, [str(e.message) for e in app.exception]
    assert any("Continuar" in button.label for button in app.button)
    continue_button=next(button for button in app.button if "Continuar" in button.label)
    continue_button.click().run()
    assert len(app.exception) == 0, [str(e.message) for e in app.exception]
    assert any("Buscar / Search" in button.label for button in app.button)
