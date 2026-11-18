"""Núcleo numérico independiente de la interfaz. Migración del calculador Tkinter.

No modifica unidades ni redondeos históricos sin pruebas de regresión.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math
from typing import Optional


TEMP_MAX_COLD = 120.0
TEMP_MAX_HOT = 200.0
INITIAL_HOT = 120.0
HOT_REFERENCE_TIME = 130.0
NEAR_LIMIT_RATIO = 0.9


def as_number(value: object) -> Optional[float]:
    """Acepta punto o coma decimal; los campos vacíos son None."""
    if value is None or value == "":
        return None
    try:
        result = float(str(value).strip().replace(",", "."))
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def display(value: object, digits: int = 3) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        v = float(value)
        return f"{v:.{digits}f}".rstrip("0").rstrip(".") if math.isfinite(v) else ""
    except (TypeError, ValueError):
        return str(value)


def convert_wr2(value: Optional[float], unit: str) -> Optional[float]:
    # Misma constante usada por leer_valor_unidad() en el código Tkinter.
    return None if value is None else value / 23.731 if unit == "lbft2" else value


def convert_mnv(value: Optional[float], unit: str) -> Optional[float]:
    return None if value is None else value / 7.233 if unit == "lbft" else value


@dataclass
class MotorInputs:
    rpm_eq: Optional[float] = None
    wr2: Optional[float] = None
    wr2_unit: str = "kgm2"
    mnv: Optional[float] = None
    mnv_unit: str = "kgm"
    is_pump: bool = True
    mmv_factor: Optional[float] = 0.33
    hp: Optional[float] = None
    rpm_motor: Optional[float] = None
    jm: Optional[float] = None
    factor_curve: Optional[float] = None
    voltage_pct: float = 100.0
    stall_hot: Optional[float] = None
    stall_cold: Optional[float] = None


@dataclass
class MotorResult:
    inputs: MotorInputs
    values: dict[str, Optional[float]] = field(default_factory=dict)
    status: str = "DATOS INSUFICIENTES"
    status_kind: str = "info"
    diagnosis: str = ""
    warnings: list[str] = field(default_factory=list)
    operations: list[tuple[str, str, str]] = field(default_factory=list)


def calculate_motor(inputs: MotorInputs) -> MotorResult:
    """Fórmulas de calcular_datos(), con errores no silenciados y divisiones seguras."""
    out = MotorResult(inputs)
    val: dict[str, Optional[float]] = {k: None for k in (
        "WR2_normal", "MNV_normal", "MMV", "JV", "MNM", "JM", "GD2M", "MMM",
        "MMV_nMot", "GD2V", "GD2V_nMot", "nGD2", "ta", "ta_ceiling",
        "ta_algebraic", "ta_physical", "torque_margin", "torque_coverage_pct",
        "hp_equilibrium", "hp_deficit", "speed_ratio", "start_feasible",
    )}
    out.values = val

    def log(var: str, equation: str, result: Optional[float]) -> None:
        out.operations.append((var, equation, display(result, 7) if result is not None else "N/A"))

    wr2 = convert_wr2(inputs.wr2, inputs.wr2_unit)
    mnv = convert_mnv(inputs.mnv, inputs.mnv_unit)
    val["WR2_normal"], val["MNV_normal"] = wr2, mnv
    if wr2 is not None:
        log("WR2", f"{inputs.wr2} ({inputs.wr2_unit}) -> kgm2", wr2)
    if mnv is not None:
        log("MNV", f"{inputs.mnv} ({inputs.mnv_unit}) -> kgm", mnv)

    voltage_factor = (min(100, max(0, inputs.voltage_pct)) / 100) ** 2
    log("Factor de voltaje", f"({inputs.voltage_pct} / 100)^2", voltage_factor)

    if mnv is not None:
        factor_mmv = 0.33 if inputs.is_pump else inputs.mmv_factor
        if factor_mmv is not None:
            val["MMV"] = mnv * factor_mmv
            log("MMV", f"{display(mnv)} x {display(factor_mmv)}", val["MMV"])
    if wr2 is not None:
        val["JV"] = wr2
        log("JV", "JV = WR2", wr2)

    if inputs.hp is not None and inputs.rpm_motor is not None:
        if inputs.hp <= 0 or inputs.rpm_motor <= 0:
            out.warnings.append("HP y RPM del motor deben ser mayores que cero.")
        else:
            mnm_base = (inputs.hp * 726.15) / inputs.rpm_motor
            val["MNM"] = round(mnm_base * voltage_factor, 2)
            log("MNM", f"({inputs.hp} x 726.15 / {inputs.rpm_motor}) x {display(voltage_factor, 5)}", val["MNM"])
            if inputs.factor_curve is not None:
                val["MMM"] = val["MNM"] * inputs.factor_curve
                log("MMM", f"{display(val['MNM'])} x {display(inputs.factor_curve)}", val["MMM"])
            else:
                out.warnings.append("Falta el factor de curvas (BT del Excel o captura manual).")

    if inputs.jm is not None:
        val["JM"] = inputs.jm
        val["GD2M"] = 4 * inputs.jm
        log("GD2M", f"4 x {display(inputs.jm, 7)}", val["GD2M"])

    if val["MMV"] is not None and inputs.rpm_eq is not None and inputs.rpm_motor is not None:
        if inputs.rpm_eq <= 0 or inputs.rpm_motor <= 0:
            out.warnings.append("Las RPM deben ser mayores que cero.")
        else:
            ratio = inputs.rpm_eq / inputs.rpm_motor
            val["MMV_nMot"] = round(val["MMV"] * ratio, 2)
            log("MMV nMot", f"{display(val['MMV'])} x ({inputs.rpm_eq} / {inputs.rpm_motor})", val["MMV_nMot"])
            if val["JV"] is not None:
                val["GD2V"] = 4 * val["JV"]
                val["GD2V_nMot"] = round(val["GD2V"] * ratio ** 2, 2)
                log("GD2V", f"4 x {display(val['JV'])}", val["GD2V"])
                log("GD2V nMot", f"{display(val['GD2V'])} x ({inputs.rpm_eq} / {inputs.rpm_motor})^2", val["GD2V_nMot"])
                if val["GD2M"] is not None:
                    val["nGD2"] = val["GD2V_nMot"] + val["GD2M"]
                    log("nGD2", f"{display(val['GD2V_nMot'])} + {display(val['GD2M'])}", val["nGD2"])

    mmm, load = val["MMM"], val["MMV_nMot"]
    if inputs.rpm_motor is not None and inputs.rpm_motor > 0 and inputs.rpm_eq is not None:
        val["speed_ratio"] = inputs.rpm_eq / inputs.rpm_motor
    if mmm is not None and load is not None:
        val["torque_margin"] = mmm - load
        val["start_feasible"] = mmm > load
        if load > 0:
            val["torque_coverage_pct"] = 100 * mmm / load
        log("Margen de par", f"{display(mmm, 7)} - {display(load, 7)}", val["torque_margin"])
        if val["torque_coverage_pct"] is not None:
            log("Cobertura de par", f"({display(mmm, 7)} / {display(load, 7)}) x 100", val["torque_coverage_pct"])
        if (inputs.rpm_motor is not None and inputs.rpm_motor > 0
                and inputs.factor_curve is not None and inputs.factor_curve > 0
                and voltage_factor > 0 and load >= 0):
            val["hp_equilibrium"] = (load * inputs.rpm_motor) / (726.15 * inputs.factor_curve * voltage_factor)
            if inputs.hp is not None:
                val["hp_deficit"] = max(0.0, val["hp_equilibrium"] - inputs.hp)
            log("HP equilibrio teórico", f"{display(load, 7)} x {inputs.rpm_motor} / (726.15 x {display(inputs.factor_curve, 7)} x {display(voltage_factor, 7)})", val["hp_equilibrium"])

    # Mantener la operación algebraica AUN si no hay par para arrancar.
    # Un valor negativo NO es un tiempo físico; es únicamente el resultado
    # de evaluar la ecuación fuera de su dominio de aplicación.
    if None not in (val["nGD2"], mmm, load, inputs.rpm_motor):
        denom = 375 * (mmm - load)
        if abs(denom) > 1e-12:
            ta_raw = (val["nGD2"] * inputs.rpm_motor) / denom
            val["ta_algebraic"] = round(ta_raw, 2)
            val["ta"] = val["ta_algebraic"]
            val["ta_ceiling"] = math.ceil(ta_raw)
            log("ta algebraico", f"({display(val['nGD2'])} x {inputs.rpm_motor}) / (375 x ({display(mmm)} - {display(load)}))", val["ta"])
            log("ta CEILING algebraico", f"ceil({display(ta_raw, 7)})", val["ta_ceiling"])
            if val["start_feasible"]:
                val["ta_physical"] = val["ta"]
        else:
            out.warnings.append("La diferencia de pares es cero: la ecuación del tiempo es indefinida (división entre cero).")

    ta = val["ta_physical"]
    hot, cold = inputs.stall_hot, inputs.stall_cold
    if val["start_feasible"] is False:
        out.status, out.status_kind = "NO SOPORTA ARRANQUE: PAR INSUFICIENTE", "bad"
        algebra = val["ta_algebraic"]
        if algebra is None:
            reason = "Los pares están equilibrados; el tiempo algebraico es indefinido."
        else:
            reason = f"La ecuación devuelve {display(algebra)} s, valor algebraico NO físico."
        out.diagnosis = (
            f"MMM={display(mmm, 5)} kgm frente a carga={display(load, 5)} kgm; "
            f"margen={display(val['torque_margin'], 5)} kgm. {reason} "
            "Se conservan los cálculos y el reporte técnico."
        )
    elif ta is None or hot is None or cold is None:
        out.status = "DATOS INSUFICIENTES"
        out.diagnosis = "Complete los datos disponibles y Stall HOT/COLD para evaluar el arranque."
    elif ta <= 0:
        out.status, out.status_kind = "NO SOPORTA ARRANQUE", "bad"
        out.diagnosis = "Tiempo de arranque no físico. Revise los parámetros."
    elif ta < hot and ta < cold:
        out.status, out.status_kind = "SOPORTA ARRANQUE EN FRÍO Y CALIENTE", "ok"
        out.diagnosis = f"ta={display(ta)} s < HOT={display(hot)} s y < COLD={display(cold)} s."
    elif ta < cold:
        out.status, out.status_kind = "SOPORTE PARCIAL: SOLO EN FRÍO", "warn"
        out.diagnosis = f"ta={display(ta)} s < COLD={display(cold)} s, pero >= HOT={display(hot)} s."
    elif ta < hot:
        out.status, out.status_kind = "SOPORTE PARCIAL: SOLO EN CALIENTE", "warn"
        out.diagnosis = f"ta={display(ta)} s < HOT={display(hot)} s, pero >= COLD={display(cold)} s."
    else:
        out.status, out.status_kind = "NO SOPORTA ARRANQUE: LÍMITE TÉRMICO", "bad"
        out.diagnosis = f"El tiempo físico ta={display(ta)} s supera los límites HOT={display(hot)} s y COLD={display(cold)} s."
    return out


def heat_status(temp: float, limit: float) -> str:
    if temp >= limit:
        return "Excede"
    if temp >= limit * NEAR_LIMIT_RATIO:
        return "Cerca"
    return "OK"


def progressive_states(rows: list[dict], limit: float) -> list[dict]:
    status = "OK"
    precedence = {"OK": 0, "Cerca": 1, "Excede": 2}
    for row in rows:
        this_status = heat_status(row["temperatura"], limit)
        if precedence[this_status] > precedence[status]:
            status = this_status
        row["estado"] = status
    return rows


@dataclass
class ConsecutiveInputs:
    f: Optional[float] = None
    gfe: Optional[float] = None
    rotor_diameter_dm: Optional[float] = None
    stack_length_dm: Optional[float] = None
    drawing: str = ""
    stator_kind: str = "std"
    stator_factor: Optional[float] = None
    starts: int = 10
    starts_hour: int = 4


@dataclass
class ConsecutiveResult:
    values: dict = field(default_factory=dict)
    cold: list[dict] = field(default_factory=list)
    hot: list[dict] = field(default_factory=list)
    hourly: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    operations: list[tuple[str, str, str]] = field(default_factory=list)


def calculate_consecutive(motor: MotorResult, data: ConsecutiveInputs) -> ConsecutiveResult:
    """Series de generar_series_arranques() y calcular_arranques_por_hora() originales."""
    out = ConsecutiveResult()
    m = motor.values
    v = {k: None for k in ("diamxlongitud", "v2a", "v2a_ceiling", "taus", "taus_ceiling",
                             "taus_ta", "v2aus", "v2aus_ceiling", "ciclo", "resto", "reposo_ciclo")}
    out.values = v

    def log(label, expr, val):
        out.operations.append((label, expr, display(val, 7)))

    if data.rotor_diameter_dm is not None and data.stack_length_dm is not None:
        v["diamxlongitud"] = ((data.rotor_diameter_dm - 0.1) * 3.1416 * 0.1 * 7.8
                              * data.stack_length_dm * 0.945)
        log("Diamxlongitud", "(diam - 0.1) x 3.1416 x 0.1 x 7.8 x longitud x 0.945", v["diamxlongitud"])

    if motor.values.get("start_feasible") is False:
        out.warnings.append(
            "Motor sin par suficiente: el tiempo algebraico se documenta, "
            "pero NO se generan gráficas térmicas ni arranques consecutivos físicos."
        )
        return out

    rpm = motor.inputs.rpm_motor
    ngd2, mmm, load, ta = m.get("nGD2"), m.get("MMM"), m.get("MMV_nMot"), m.get("ta")
    if (None not in (ngd2, rpm, mmm, load, data.f, data.gfe)
            and data.gfe != 0 and mmm != load):
        raw = (ngd2 * rpm ** 2 * mmm * data.f) / (730 * (mmm - load) * 460 * data.gfe)
        v["v2a"] = round(raw, 2)
        v["v2a_ceiling"] = round(v["v2a"], 0)  # Legado: round, NO math.ceil.
        log("V'2A", "nGD2 x RPM² x MMM x f / (730 x (MMM - MMV_nMot) x 460 x GFe)", v["v2a"])
        log("V'2A CEILING", "round(V'2A, 0) [comportamiento del original]", v["v2a_ceiling"])
    if None not in (ngd2, rpm, load) and load != 0:
        v["taus"] = round((ngd2 * rpm) / (375 * load), 2)
        v["taus_ceiling"] = round(v["taus"], 0)
        log("taus", "nGD2 x RPM / (375 x MMV_nMot)", v["taus"])
        log("taus CEILING", "round(taus, 0)", v["taus_ceiling"])
    if v["taus_ceiling"] is not None and ta not in (None, 0):
        v["taus_ta"] = v["taus_ceiling"] / ta
    if data.stator_factor is not None and v["v2a_ceiling"] is not None:
        v["v2aus"] = data.stator_factor * v["v2a_ceiling"]
        v["v2aus_ceiling"] = math.floor(v["v2aus"])
        log("V2aus", "factor_estator x V'2A CEILING", v["v2aus"])

    n = max(1, min(500, int(data.starts)))
    if n != data.starts:
        out.warnings.append("Número de arranques limitado a 500 por protección de recursos.")

    vc, vs, tc = v["v2a_ceiling"], v["v2aus_ceiling"], v["taus_ceiling"]
    factor = data.stator_factor
    if None not in (vc, vs, tc, factor, ta):
        prev_cool: Optional[float] = None
        for i in range(1, n + 1):
            heat = vc if i == 1 else prev_cool + vc
            out.cold.append(dict(arranque=str(i), temperatura=heat, segundos=ta, tipo="calentamiento",
                                 operacion="Tcal = V'2A" if i == 1 else "Tcal = Tenf_previo + V'2A"))
            cool = vs if i == 1 else heat * factor
            out.cold.append(dict(arranque="", temperatura=cool, segundos=tc, tipo="enfriamiento",
                                 operacion="Tenf = V2aus_ceiling" if i == 1 else "Tenf = Tcal x factor_estator"))
            prev_cool = cool
        progressive_states(out.cold, TEMP_MAX_COLD)

        # Referencia en frío + fase inicial caliente + n arranques posteriores.
        out.hot.extend([
            dict(arranque="En frío", temperatura=vc, segundos=ta, tipo="calentamiento", operacion="T = V'2A"),
            dict(arranque="", temperatura=vs, segundos=tc, tipo="enfriamiento", operacion="T = V2aus_ceiling"),
        ])
        hot_heat = INITIAL_HOT + vc
        hot_cool = hot_heat - vs
        out.hot.extend([
            dict(arranque="En caliente", temperatura=hot_heat, segundos=HOT_REFERENCE_TIME,
                 tipo="calentamiento", operacion="T = 120 + V'2A"),
            dict(arranque="", temperatura=hot_cool, segundos=tc, tipo="enfriamiento", operacion="T = Tcal - V2aus_ceiling"),
        ])
        prev_cool = hot_cool
        for i in range(1, n + 1):
            heat = prev_cool + vc
            out.hot.append(dict(arranque=str(i), temperatura=heat, segundos=ta, tipo="calentamiento", operacion="Tcal = Tenf + V'2A"))
            cool = heat - vs
            out.hot.append(dict(arranque="", temperatura=cool, segundos=tc, tipo="enfriamiento", operacion="Tenf = Tcal - V2aus_ceiling"))
            prev_cool = cool
        progressive_states(out.hot, TEMP_MAX_HOT)

        nh = max(1, min(500, int(data.starts_hour)))
        cycle = ta + tc
        remaining = max(0.0, 3600 - cycle * nh)
        rest_cycle = remaining / nh
        v["ciclo"], v["resto"], v["reposo_ciclo"] = cycle, remaining, rest_cycle
        if cycle * nh > 3600:
            out.warnings.append("Inviable: los arranques y enfriamientos no caben en una hora.")
        b5 = ta + tc + rest_cycle  # fórmula original: descuento térmico fijo B5/60
        out.hourly.append(dict(arranque="", tiempo=0.0, temperatura=0.0, tipo="inicio", operacion="Referencia inicial"))
        prev_t, prev_temp = 0.0, 0.0
        for i in range(1, nh + 1):
            heat_t = prev_t + ta
            heat_temp = vc + prev_temp
            out.hourly.append(dict(arranque=str(i), tiempo=heat_t, temperatura=heat_temp,
                                   tipo="calentamiento", operacion="t = t_previo + ta; T = T_previa + V'2A"))
            cool_t = heat_t + tc
            cool_temp = heat_temp * factor
            out.hourly.append(dict(arranque="", tiempo=cool_t, temperatura=cool_temp,
                                   tipo="enfriamiento", operacion="t = tcal + taus; T = Tcal x factor"))
            rest_t = cool_t + rest_cycle
            rest_temp = max(0.0, cool_temp - b5 / 60)
            out.hourly.append(dict(arranque="", tiempo=rest_t, temperatura=rest_temp,
                                   tipo="reposo", operacion="t = tenf + reposo; T = max(0, Tenf - B5/60)"))
            prev_t, prev_temp = rest_t, rest_temp
        progressive_states(out.hourly, TEMP_MAX_HOT)
    else:
        out.warnings.append("Complete f, GFe, factor del estator y un cálculo válido del motor para simular.")
    return out
