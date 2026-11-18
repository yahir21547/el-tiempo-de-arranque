import math
import pytest
from core.engine import (
    MotorInputs, ConsecutiveInputs, calculate_motor, calculate_consecutive,
    heat_status, progressive_states, as_number, convert_wr2,convert_mnv,
)


def reference():
    data=MotorInputs(rpm_eq=1750,wr2=50,mnv=20,wr2_unit="kgm2",mnv_unit="kgm",
                     is_pump=True,hp=500,rpm_motor=1800,jm=10,factor_curve=1.35,
                     voltage_pct=100,stall_hot=15,stall_cold=20)
    result=calculate_motor(data)
    return data,result


def test_original_motor_formula():
    i,r=reference()
    mnm=round((500*726.15/1800),2)
    mmm=mnm*1.35
    mmv=20*.33
    load=round(mmv*(1750/1800),2)
    gd2v=4*50
    gd2v_n=round(gd2v*(1750/1800)**2,2)
    total=gd2v_n+40
    ta_raw=(total*1800)/(375*(mmm-load))
    assert r.values["MNM"]==mnm
    assert r.values["MMV"]==mmv
    assert r.values["MMM"]==mmm
    assert r.values["GD2V_nMot"]==gd2v_n
    assert r.values["ta"]==round(ta_raw,2)
    assert r.values["ta_ceiling"]==math.ceil(ta_raw)
    assert r.status_kind=="ok"


def test_no_start_when_load_torque_exceeds_motor_torque():
    i,r=reference()
    i.mnv=2000
    r=calculate_motor(i)
    assert r.status_kind=="bad"
    assert r.values["start_feasible"] is False
    assert r.values["ta"] is not None and r.values["ta"] < 0
    assert r.values["ta_algebraic"] == r.values["ta"]
    assert r.values["ta_physical"] is None
    assert r.values["torque_margin"] < 0
    assert r.values["hp_equilibrium"] > i.hp
    assert "NO físico" in r.diagnosis


def test_zero_load_does_not_suppress_startup_time():
    i,r=reference()
    i.mnv=0
    r=calculate_motor(i)
    assert r.values["MMV_nMot"]==0
    assert r.values["ta"] is not None


def test_curve_factor_is_required_in_manual_mode():
    i,_=reference()
    i.factor_curve=None
    r=calculate_motor(i)
    assert r.values["MMM"] is None
    assert r.values["ta"] is None


def test_conversion_preserves_legacy_constants():
    assert convert_wr2(23.731,"lbft2")==pytest.approx(1)
    assert convert_mnv(7.233,"lbft")==pytest.approx(1)
    assert as_number("2,45")==pytest.approx(2.45)
    assert as_number("not a number") is None


def test_consecutive_thermal_series_complete():
    _,motor=reference()
    inp=ConsecutiveInputs(f=.8,gfe=30,rotor_diameter_dm=4,stack_length_dm=8,
                          stator_kind="std",stator_factor=.7,starts=10,starts_hour=4)
    r=calculate_consecutive(motor,inp)
    assert r.values["v2a"] is not None
    assert r.values["v2aus_ceiling"] is not None
    assert len(r.cold)==20
    assert len(r.hot)==24
    assert len(r.hourly)==13
    assert r.hourly[0]["tiempo"]==0
    assert r.values["ciclo"]==motor.values["ta"]+r.values["taus_ceiling"]
    assert r.hourly[-1]["tiempo"]==pytest.approx(3600)


def test_temperature_colors():
    assert heat_status(107.9,120)=="OK"
    assert heat_status(108,120)=="Cerca"
    assert heat_status(120,120)=="Excede"
    rows=progressive_states([{"temperatura":121},{"temperatura":80}],120)
    assert [x["estado"] for x in rows]==["Excede","Excede"]


def test_hourly_infeasible_detection():
    _,motor=reference()
    r=calculate_consecutive(motor,ConsecutiveInputs(f=.8,gfe=30,stator_factor=.7,starts_hour=500))
    assert any("Inviable" in w for w in r.warnings)


def test_pdf_generates_valid_bytes():
    from reports.pdf_report import generate_pdf
    _,motor=reference()
    c=calculate_consecutive(motor,ConsecutiveInputs(f=.8,gfe=30,stator_factor=.7,starts=4,starts_hour=2))
    data=generate_pdf(motor,c,"1LE43214BB1")
    assert data.startswith(b"%PDF")
    assert len(data)>5000


def test_insufficient_torque_screenshot_scenario_remains_calculable():
    motor=MotorInputs(
        hp=1,rpm_motor=1800,jm=.0064686,
        stall_hot=18,stall_cold=26,factor_curve=2.5962,
        rpm_eq=3600,wr2=12,mnv=12,is_pump=True,voltage_pct=100,
    )
    r=calculate_motor(motor)
    assert r.values["MNM"] == .4
    assert r.values["MMM"] == pytest.approx(1.03848)
    assert r.values["MMV_nMot"] == pytest.approx(7.92)
    assert r.status_kind == "bad"
    assert r.values["ta"] < 0
    assert r.values["ta_physical"] is None
    assert r.values["torque_coverage_pct"] == pytest.approx(100*1.03848/7.92)
    assert r.values["hp_equilibrium"] > 7
    assert r.values["ta_ceiling"] is not None
    assert r.values["nGD2"] == pytest.approx(192.0258744)


def test_equal_torque_is_indeterminate_but_generates_pdf():
    motor=MotorInputs(hp=100,rpm_motor=1800,jm=1,rpm_eq=1800,wr2=10,
                      mnv=10,is_pump=False,mmv_factor=1,
                      factor_curve=10/(round(100*726.15/1800,2)),
                      stall_hot=20,stall_cold=30)
    r=calculate_motor(motor)
    assert r.values["torque_margin"] == pytest.approx(0)
    assert r.status_kind == "bad"
    assert r.values["ta"] is None
    from reports.pdf_report import generate_pdf
    assert generate_pdf(r,None,"CASO-INDEFINIDO").startswith(b"%PDF")


def test_no_thermal_simulation_if_motor_cannot_accelerate():
    i,_=reference()
    i.mnv=2000
    m=calculate_motor(i)
    cons=calculate_consecutive(m,ConsecutiveInputs(
        f=.8,gfe=30,stator_factor=.7,starts=10,starts_hour=4,
    ))
    assert cons.cold==cons.hot==cons.hourly==[]
    assert any("NO" in warning for warning in cons.warnings)


def test_no_start_generates_pdf_and_preserves_diagnostics():
    i,_=reference()
    i.mnv=2000
    m=calculate_motor(i)
    from reports.pdf_report import generate_pdf
    pdf=generate_pdf(m,None,"1LE43214BB1")
    assert pdf.startswith(b"%PDF")
    assert len(pdf)>3000
