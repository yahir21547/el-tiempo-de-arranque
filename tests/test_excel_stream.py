"""Pruebas del lector ligero de Excel, sin cargar la hoja entera."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from openpyxl import Workbook

from services.motors import (
    DEFAULT_COLS, MotorDataError, SHEET_NAME,
    lookup_motor_stream, validate_workbook_stream,
)


MLFB = "1LE43521ABA"


def sample_book():
    book=Workbook()
    sheet=book.active
    sheet.title=SHEET_NAME
    for col,title in [(1,"MLFB"),(3,"HP"),(45,"Inertia"),(40,"HOT"),
                      (41,"COLD"),(72,"Curve")]:
        sheet.cell(3,col,title)
    for col,value in [(1,MLFB),(3,100.0),(45,23.73),(40,10.0),
                      (41,16.0),(72,145.0)]:
        sheet.cell(4,col,value)
    output=BytesIO()
    book.save(output)
    book.close()
    return output.getvalue()


class TestExcelStreaming(unittest.TestCase):
    def test_lookup_bytes_preserves_original_mapping(self):
        motor=lookup_motor_stream(sample_book(),MLFB,DEFAULT_COLS)
        self.assertEqual(motor.mlfb,MLFB)
        self.assertEqual(motor.hp,100.0)
        self.assertAlmostEqual(motor.jm,1.0)
        self.assertAlmostEqual(motor.curve_factor,1.45)
        self.assertEqual(motor.stall_hot,10.0)
        self.assertEqual(motor.stall_cold,16.0)
        self.assertEqual(motor.rpm_motor,1800)

    def test_lookup_from_path(self):
        with TemporaryDirectory() as tmp:
            file=Path(tmp)/"base.xlsx"
            file.write_bytes(sample_book())
            self.assertEqual(lookup_motor_stream(file,MLFB,DEFAULT_COLS).hp,100.0)

    def test_validate_workbook(self):
        report=validate_workbook_stream(sample_book(),DEFAULT_COLS)
        self.assertEqual(report["mlfb_validos"],1)
        self.assertEqual(report["columnas"],72)

    def test_no_matching_code_raises(self):
        with self.assertRaises(MotorDataError):
            lookup_motor_stream(sample_book(),"1LE43521ACA",DEFAULT_COLS)

    def test_invalid_columns_raises(self):
        with self.assertRaises(MotorDataError):
            lookup_motor_stream(sample_book(),MLFB,{**DEFAULT_COLS,"curve":"ZZ"})


if __name__=="__main__":
    unittest.main()
