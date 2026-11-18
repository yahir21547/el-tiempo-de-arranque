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


def test_calculator_exports_pdf_even_with_insufficient_motor_torque():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/"streamlit_app.py"),default_timeout=40)
    app.session_state["screen"]="calculator"
    for name,value in {
        "hp":"1","rpm_motor":"1800","jm":"0.0064686","factor_curve":"2.5962",
        "stall_hot":"18","stall_cold":"26","rpm_eq":"3600",
        "wr2":"12","mnv":"12",
    }.items():
        app.session_state[name]=value
    app.run()
    assert len(app.exception)==0, [str(e.message) for e in app.exception]
    assert any("Exportar informe PDF" in b.label for b in app.get("button")) or any(
        "Exportar informe PDF" in b.label for b in app.get("download_button")
    )
    assert any("Evaluar" in b.label for b in app.button)
    button=next(b for b in app.button if "Evaluar" in b.label)
    button.click().run()
    assert len(app.exception)==0, [str(e.message) for e in app.exception]
    assert app.session_state["hp"]=="1"
    # Acepta resultado algebraico no físico, sin modificar el input.
    assert any("NO SOPORTA" in str(e.message) or "NO físico" in str(e.message)
               for e in app.error)
