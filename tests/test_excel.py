import pandas as pd
import pytest
from services.motors import MotorDataError,DEFAULT_COLS,excel_col_index,lookup_motor,validate_workbook


def test_excel_letter_mapping():
    assert excel_col_index("A")==0
    assert excel_col_index("Z")==25
    assert excel_col_index("AA")==26
    assert excel_col_index("AS")==44
    assert excel_col_index("BT")==71
    with pytest.raises(MotorDataError):excel_col_index("A6")


def fake_frame():
    # Simula la selección de columna por posición .iloc del original.
    df=pd.DataFrame([[None]*72 for _ in range(4)])
    code="1LE43214BB1"
    df.iat[2,0]=code
    df.iat[2,2]=100
    df.iat[2,44]=23.73
    df.iat[2,71]=110
    df.iat[2,39]=9    # AN (índice 39)
    df.iat[2,40]=15   # AO (índice 40)
    return df


def test_mlfb_record_legacy_mapping():
    frame=fake_frame()
    validate_workbook(frame,DEFAULT_COLS)
    r=lookup_motor(frame,"1le43214bb1",DEFAULT_COLS)
    assert r.hp==100
    assert r.jm==1
    assert r.curve_factor==1.10
    assert r.stall_hot==9
    assert r.stall_cold==15
    assert r.rpm_motor==1800


def test_invalid_mlfb_rejected():
    with pytest.raises(MotorDataError):lookup_motor(fake_frame(),"SHORT",DEFAULT_COLS)
