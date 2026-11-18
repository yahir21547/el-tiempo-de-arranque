"""Acceso a la base PMD NEMA, con correspondencias editables de columnas."""
from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import pandas as pd

SHEET_NAME = "Core Level Data 60 Hz"
DEFAULT_COLS = {
    "mlfb": "A", "hp": "C", "inertia": "AS", "curve": "BT", "hot": "AN", "cold": "AO",
}


class MotorDataError(ValueError):
    pass


def excel_col_index(letter: str) -> int:
    s = letter.upper().strip()
    if not s or not s.isalpha() or not s.isascii():
        raise MotorDataError(f"Columna Excel inválida: {letter!r}")
    n = 0
    for ch in s:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def read_motors(source: bytes | str | Path) -> pd.DataFrame:
    """Equivalencia a pd.read_excel(sheet_name=..., header=2) del original."""
    data = BytesIO(source) if isinstance(source, bytes) else source
    try:
        return pd.read_excel(data, sheet_name=SHEET_NAME, header=2, engine="openpyxl")
    except Exception as exc:
        raise MotorDataError(f"No se pudo leer la hoja '{SHEET_NAME}': {exc}") from exc


def validate_columns(frame: pd.DataFrame, columns: dict[str, str]) -> None:
    missing = [f"{name} ({code})" for name, code in columns.items()
               if excel_col_index(code) >= frame.shape[1]]
    if missing:
        raise MotorDataError(f"Las siguientes columnas no existen en el archivo: {', '.join(missing)}. "
                             f"El archivo contiene {frame.shape[1]} columnas.")


def validate_workbook(frame: pd.DataFrame, columns: dict[str, str]) -> dict:
    validate_columns(frame, columns)
    col = excel_col_index(columns["mlfb"])
    series = frame.iloc[:, col].dropna().astype(str).str.strip().str.upper()
    valid = series.str.fullmatch(r"[A-Z0-9]{11}", na=False).sum()
    if not valid:
        raise MotorDataError("No se encontraron códigos MLFB de 11 caracteres en la columna seleccionada. "
                             "Revise la versión del archivo y la correspondencia de columnas.")
    return {"filas": int(len(frame)), "mlfb_validos": int(valid), "columnas": int(frame.shape[1])}


def required_float(value: object, field: str) -> float:
    try:
        if pd.isna(value):
            raise ValueError()
        val = float(str(value).strip().replace(",", "."))
        if not pd.notna(val):
            raise ValueError()
        return val
    except (ValueError, TypeError) as exc:
        raise MotorDataError(f"El dato '{field}' no es numérico: {value!r}") from exc


@dataclass
class MotorRecord:
    mlfb: str
    hp: float
    jm: float
    curve_factor: float
    stall_hot: float
    stall_cold: float
    rpm_motor: int | None
    row_index: int


def lookup_motor(frame: pd.DataFrame, code: str, columns: dict[str, str]) -> MotorRecord:
    validate_columns(frame, columns)
    code = code.strip().upper()
    if len(code) != 11 or not code.isalnum():
        raise MotorDataError("El MLFB debe tener exactamente 11 caracteres alfanuméricos.")
    cl = {k: excel_col_index(v) for k, v in columns.items()}
    series = frame.iloc[:, cl["mlfb"]].astype(str).str.strip().str.upper()
    matches = frame.loc[series == code]
    if matches.empty:
        raise MotorDataError(f"No se encontró el código '{code}' en el archivo activo.")
    pos = frame.index.get_loc(matches.index[0])
    row = matches.iloc[0]
    hp = required_float(row.iloc[cl["hp"]], "HP")
    inertia = required_float(row.iloc[cl["inertia"]], "Inercia")
    curve = required_float(row.iloc[cl["curve"]], "Curvas")
    hot = required_float(row.iloc[cl["hot"]], "Stall HOT")
    cold = required_float(row.iloc[cl["cold"]], "Stall COLD")
    rpm = {"A": 3600, "B": 1800, "C": 1200, "D": 900}.get(code[9])
    return MotorRecord(code, hp, inertia / 23.73, curve / 100, hot, cold, rpm, int(pos))
