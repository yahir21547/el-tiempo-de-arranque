"""Plataforma de cálculos de motores: migración funcional de Tkinter a Streamlit.

Ejecutar: streamlit run streamlit_app.py
Fuente de datos: PMD NEMA V46 del repositorio GitHub original.
"""
from __future__ import annotations
import hashlib
from io import BytesIO
import json
from datetime import date
from pathlib import Path
from html import escape
from typing import Any

print('[MOTOR-BOOT] Inicio de script Python', flush=True)
import pandas as pd
import streamlit as st

from core.engine import (
    MotorInputs, MotorResult, ConsecutiveInputs, ConsecutiveResult,
    calculate_motor, calculate_consecutive, as_number, display,
    TEMP_MAX_COLD, TEMP_MAX_HOT,
)
from services.motors import (
    DEFAULT_COLS, MotorDataError, lookup_motor_stream,
    validate_workbook_stream, validate_column_codes,
)
from services.resources import EXCEL_NAME, ensure_resource, optional_resource, public_resource_url
from services.charts import thermal_chart
from services.persistence import github_settings, validate_admin, persist_to_github, PersistenceError
from reports.pdf_report import generate_pdf
print('[MOTOR-BOOT] Módulos importados correctamente', flush=True)

st.set_page_config(
    page_title="Cálculo de Tiempo de Arranque | Motor Calculations",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
:root {--abb:#d81e05;--navy:#253449;--line:#cbd5e1;--muted:#67788b;--paper:#fff;}
[data-testid="stAppViewContainer"] {background:linear-gradient(155deg,#e5ebf2 0%,#eef2f6 45%,#dfe6ee 100%);}
[data-testid="stHeader"] {background:transparent;}
.block-container {max-width:1580px; padding-top:1.15rem; padding-bottom:5rem;}
[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {gap:.62rem;}
[data-testid="stVerticalBlockBorderWrapper"] {background:#fff; border:1px solid #cbd5e1!important; border-radius:11px!important; box-shadow:0 2px 6px #2d405512;}
div[data-testid="stTextInput"] label p,div[data-testid="stNumberInput"] label p,div[data-testid="stSelectbox"] label p {font-weight:600;color:#2e3b50;font-size:.84rem;}
.stTextInput input,.stNumberInput input {border-color:#cbd5e1!important;background:#fff!important;min-height:2.35rem!important;}
.stTextInput input:disabled {color:#1b3c54!important;background:#f0f4f9!important;opacity:1;-webkit-text-fill-color:#1b3c54!important;}
.stButton button[kind="primary"],div[data-testid="stDownloadButton"] button[kind="primary"] {background:#d81e05!important;border-color:#d81e05!important;color:#fff!important;font-weight:700!important;}
.stButton button {border-radius:6px;}
.stButton button:hover {border-color:#b71805!important; color:#b71805!important;}
.stButton button[kind="primary"]:hover {background:#b71805!important;color:#fff!important;}
[data-testid="stMetric"] {background:#f5f8fc;border:1px solid #d8e0e9;border-radius:8px;padding:.85rem!important;}
[data-testid="stMetricLabel"] {color:#536478;}
[data-testid="stMetricValue"] {font-size:1.55rem;}
[data-testid="stFileUploader"] {background:#f8fafc;border-radius:8px;}
[data-testid="stHorizontalBlock"] {gap:.9rem;}
.abb-hero {background:linear-gradient(112deg,#172d43,#304b63);color:white;border-left:6px solid #d81e05;
 border-radius:10px;padding:19px 23px;margin:0 0 14px 0;box-shadow:0 3px 12px #1b2d4329;}
.abb-hero h1 {color:white!important;font-size:1.7rem!important;line-height:1.15;margin:0 0 5px!important;}
.abb-hero p {color:#d9e5f2!important;margin:0;font-size:.88rem;}
.abb-section {font-size:1.11rem;font-weight:800;letter-spacing:.1px;color:#243951;margin:4px 0 7px;}
.abb-line {width:100%;height:3px;background:linear-gradient(90deg,#d81e05,#e5ebf2 55%);margin:1px 0 9px;}
.abb-diagnosis {padding:14px 19px;border-radius:9px;margin:6px 0 15px;border-left:7px solid #678;}
.abb-diagnosis strong {display:block;font-size:1.03rem;margin-bottom:5px;}
.abb-diagnosis small {font-size:.87rem;line-height:1.4;}
.abb-diagnosis.ok {background:#eaf5ee;border-color:#2e7d32;color:#18522d;}
.abb-diagnosis.warn {background:#fff3cd;border-color:#d4a300;color:#694b07;}
.abb-diagnosis.bad {background:#fdecea;border-color:#c00000;color:#7f1b18;}
.abb-diagnosis.info {background:#e6eff8;border-color:#4779a0;color:#2a4a68;}
.abb-caption {font-size:.77rem;color:#64748b;margin:0 0 8px 0;}
.abb-chip {font-size:.73rem;display:inline-block;background:#e8eef6;padding:4px 8px;border-radius:5px;color:#2b4c67;font-weight:700;}
.abb-status-fld {font-size:.77rem;color:#2e7d32;font-weight:700;}
.abb-headline {font-size:1.15rem;font-weight:800;color:#243951;}
@media (max-width:840px){.block-container{padding-left:.55rem;padding-right:.55rem}.abb-hero{padding:13px}.abb-hero h1{font-size:1.24rem!important}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

MODEL_KEYS = [
    "mlfb", "rpm_eq", "wr2", "mnv", "hp", "rpm_motor", "jm",
    "stall_hot", "stall_cold", "factor_mmv", "factor_curve",
    "f", "gfe", "rotor_diameter", "stack_length", "drawing", "stator_std",
    "stator_deep", "stator_double", "number_starts", "starts_hour", "is_pump",
    "wr2_unit", "mnv_unit", "stator_kind", "voltage_slider", "voltage_number",
    "enable_consecutive", "unlock_motor", "auto_calculate",
]
DEFAULTS: dict[str, Any] = {
    "screen": "home", "selection": "Cálculo de Tiempo de Arranque / Start-Up Time Calculation",
    "mlfb": "", "rpm_eq": "", "wr2": "", "mnv": "", "hp": "", "rpm_motor": "",
    "jm": "", "stall_hot": "", "stall_cold": "", "factor_mmv": "0.33", "factor_curve": "",
    "f": "", "gfe": "", "rotor_diameter": "", "stack_length": "", "drawing": "",
    "stator_std": "", "stator_deep": "", "stator_double": "", "number_starts": 10,
    "starts_hour": 4, "stator_kind": "std", "is_pump": True, "wr2_unit": "kgm2",
    "mnv_unit": "kgm", "voltage_slider": 100, "voltage_number": 100,
    "enable_consecutive": False, "unlock_motor": False, "auto_calculate": True,
    "motor_found": False, "custom_excel_bytes": None, "custom_excel_hash": "",
    "active_excel_name": EXCEL_NAME, "upload_epoch": 0, "notice": "",
    "current_map": DEFAULT_COLS.copy(), "source_version": "V46 (repositorio original)", "import_error": "", "search_error": "",
}
for key,val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val.copy() if isinstance(val,dict) else val
for code, col in DEFAULT_COLS.items():
    if f"cfg_{code}" not in st.session_state:
        st.session_state[f"cfg_{code}"] = col
ss = st.session_state


def current_excel() -> tuple[bytes | Path | None,str,str]:
    """Resuelve la fuente del Excel SOLO cuando se pulsa Buscar.
    Nunca carga todas las filas de la hoja al renderizar la pantalla.
    """
    if ss["custom_excel_bytes"] is not None:
        return ss["custom_excel_bytes"], ss["active_excel_name"], ""
    try:
        return ensure_resource("data/" + EXCEL_NAME), EXCEL_NAME, ""
    except Exception as exc:
        return None, "", str(exc)


def field_value(key: str):
    return as_number(ss[key])


def motor_inputs() -> MotorInputs:
    return MotorInputs(
        rpm_eq=field_value("rpm_eq"),wr2=field_value("wr2"),wr2_unit=ss["wr2_unit"],
        mnv=field_value("mnv"),mnv_unit=ss["mnv_unit"],is_pump=ss["is_pump"],
        mmv_factor=.33 if ss["is_pump"] else field_value("factor_mmv"),
        hp=field_value("hp"),rpm_motor=field_value("rpm_motor"),jm=field_value("jm"),
        factor_curve=field_value("factor_curve"),voltage_pct=float(ss["voltage_slider"]),
        stall_hot=field_value("stall_hot"),stall_cold=field_value("stall_cold"),
    )


def consecutive_inputs() -> ConsecutiveInputs:
    factor_keys={"std":"stator_std","ranura_profunda":"stator_deep","doble_cuadro":"stator_double"}
    return ConsecutiveInputs(
        f=field_value("f"),gfe=field_value("gfe"),
        rotor_diameter_dm=field_value("rotor_diameter"),stack_length_dm=field_value("stack_length"),
        drawing=ss["drawing"],stator_kind=ss["stator_kind"],
        stator_factor=field_value(factor_keys[ss["stator_kind"]]),
        starts=int(ss["number_starts"]),starts_hour=int(ss["starts_hour"]),
    )


def reset_model():
    for key in MODEL_KEYS:
        val=DEFAULTS[key]
        ss[key] = val.copy() if isinstance(val,dict) else val
    ss["motor_found"] = False
    ss["notice"] = "Formulario reiniciado. La base Excel se conserva cargada."


def restore_column_map():
    for k,v in DEFAULT_COLS.items():
        ss[f"cfg_{k}"]=v
    ss["current_map"]=DEFAULT_COLS.copy()
    ss["notice"]="Columnas originales restauradas."


def callback_import_project():
    uploaded=ss.get("imported_json")
    if uploaded is None:
        ss["import_error"]="Seleccione un archivo de proyecto JSON."
        return
    try:
        import_project(uploaded.getvalue())
        ss["import_error"]=""
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        ss["import_error"]=f"Proyecto inválido: {exc}"


def save_project() -> bytes:
    project={"schema":1,"app":"Cálculo de Tiempo de Arranque","saved_at":date.today().isoformat(),
             "inputs":{k:ss[k] for k in MODEL_KEYS}, "columns":ss["current_map"],
             "database":ss["active_excel_name"],"source_version":ss["source_version"]}
    return json.dumps(project,ensure_ascii=False,indent=2).encode("utf-8")


def import_project(data: bytes):
    if len(data)>150_000:
        raise ValueError("El proyecto excede el tamaño permitido (150 KB).")
    project=json.loads(data.decode("utf-8-sig"))
    if not isinstance(project,dict) or project.get("schema") != 1 or not isinstance(project.get("inputs"),dict):
        raise ValueError("El archivo no corresponde a un proyecto de esta aplicación.")
    values=project["inputs"]
    selected=values.get("stator_kind","std")
    if selected not in ("std","ranura_profunda","doble_cuadro"):
        raise ValueError("Tipo de estator no reconocido.")
    if values.get("wr2_unit","kgm2") not in ("kgm2","lbft2") or values.get("mnv_unit","kgm") not in ("kgm","lbft"):
        raise ValueError("Unidades inválidas.")
    for key in ("number_starts","starts_hour"):
        if key in values and not (type(values[key]) is int and 1 <= values[key] <= 500):
            raise ValueError(f"Valor no permitido: {key}.")
    for key in ("voltage_slider","voltage_number"):
        if key in values and not (type(values[key]) is int and 0 <= values[key] <= 100):
            raise ValueError(f"Valor no permitido: {key}.")
    for k,v in values.items():
        if k in MODEL_KEYS and type(v) is type(DEFAULTS[k]):
            if isinstance(v,str) and len(v)>250:
                raise ValueError(f"Texto excesivamente largo: {k}.")
            ss[k]=v
    original_map=project.get("columns",{})
    if isinstance(original_map,dict) and set(original_map)==set(DEFAULT_COLS):
        for k,letter in original_map.items():
            if isinstance(letter,str) and 1<=len(letter)<=3 and letter.isascii() and letter.isalpha():
                ss[f"cfg_{k}"]=letter.upper()
        ss["current_map"]={k:ss[f"cfg_{k}"] for k in DEFAULT_COLS}
    ss["motor_found"] = False
    ss["unlock_motor"] = True
    ss["notice"] = "Proyecto cargado; verifique que la versión de Excel sea la esperada."


def search_motor_callback():
    """Callback se ejecuta antes de montar widgets y evita SessionStateError."""
    ss["search_error"]=""
    print("[MOTOR-LOOKUP] Búsqueda MLFB solicitada", flush=True)
    source,_,error=current_excel()
    if source is None:
        ss["search_error"]=error or "No está disponible la base Excel."
        print("[MOTOR-LOOKUP] Falló descarga de Excel: " + ss["search_error"], flush=True)
        return
    try:
        print("[MOTOR-LOOKUP] Libro obtenido; iniciando consulta streaming", flush=True)
        motor=lookup_motor_stream(source,ss["mlfb"],ss["current_map"])
        print("[MOTOR-LOOKUP] Motor encontrado sin cargar la hoja completa", flush=True)
        record={"hp":motor.hp,"rpm_motor":motor.rpm_motor,"jm":motor.jm,
                "stall_hot":motor.stall_hot,"stall_cold":motor.stall_cold,"factor_curve":motor.curve_factor}
        for k,v in record.items():ss[k]=display(v,7)
        ss["motor_found"]=True
        ss["unlock_motor"]=False
        ss["notice"]=f"Motor {motor.mlfb} cargado correctamente. Revise los datos del equipo accionado."
    except MotorDataError as exc:
        ss["search_error"]=str(exc)


def input_field(label: str, key: str, helptext: str | None=None, disabled: bool=False, placeholder: str=""):
    return st.text_input(label,key=key,help=helptext,disabled=disabled,placeholder=placeholder)


def readonly(label: str, value: float | None, unit: str=""):
    st.text_input(label,value=(display(value,6)+(f" {unit}" if unit and value is not None else "")),disabled=True)


def section(text: str):
    st.markdown(f'<div class="abb-section">{escape(text)}</div><div class="abb-line"></div>',unsafe_allow_html=True)


def render_diagnosis(result: MotorResult):
    st.markdown(
        f'<div class="abb-diagnosis {result.status_kind}"><strong>{escape(result.status)}</strong>'
        f'<small>{escape(result.diagnosis)}</small></div>',unsafe_allow_html=True)


def on_voltage_slider():
    ss["voltage_number"] = ss["voltage_slider"]


def on_voltage_number():
    ss["voltage_slider"] = ss["voltage_number"]


def status_table(rows: list[dict],hourly=False):
    if not rows:
        st.info("Sin resultados. Complete los campos de la simulación.")
        return
    df=pd.DataFrame(rows)
    columns=["arranque","tiempo","temperatura","tipo","estado"] if hourly else ["arranque","temperatura","segundos","tipo","estado"]
    df=df[columns].rename(columns={"arranque":"Arr.","tiempo":"t (seg)","temperatura":"°C",
                                    "segundos":"Seg / Sec","tipo":"Tipo / Type","estado":"Estado"})
    colors={"OK":"#eaf5ee","Cerca":"#fff3cd","Excede":"#fdecea"}
    styled=(df.style.apply(lambda row: [f"background-color:{colors.get(row['Estado'],'#fff')}" for _ in row],axis=1)
                 .format({"°C":"{:.3f}",**({"t (seg)":"{:.3f}"} if hourly else {"Seg / Sec":"{:.3f}"})}))
    st.dataframe(styled,hide_index=True,width="stretch",height=min(350,40+35*len(df)))


@st.dialog("Operaciones utilizadas / Operations Used",width="large")
def operations_dialog(motor: MotorResult, cons: ConsecutiveResult | None):
    tab1,tab2=st.tabs(["Detalle / Details","Tablas / Tables"])
    with tab1:
        ops=list(motor.operations)+(cons.operations if cons else [])
        if ops:
            st.dataframe(pd.DataFrame(ops,columns=["Variable","Operación aplicada","Resultado"]),hide_index=True,width="stretch")
            st.download_button("Descargar operaciones CSV",pd.DataFrame(ops,columns=["Variable","Operación","Resultado"]).to_csv(index=False).encode("utf-8-sig"),"operaciones_motor.csv",mime="text/csv")
        else:st.info("Ingrese datos y ejecute un cálculo.")
    with tab2:
        if cons and (cons.cold or cons.hot or cons.hourly):
            for title,rows in [("Arranques en frío",cons.cold),("Arranques en caliente",cons.hot),("Arranques por hora",cons.hourly)]:
                st.markdown("**"+title+"**")
                st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch",height=215)
        else:
            st.info("Active y complete Arranques consecutivos para ver las tablas de operaciones.")


def header():
    col1,col2,col3=st.columns([1,7,1.1],vertical_alignment="center")
    with col1:
        logo=optional_resource("assets/logo.png")
        st.image(str(logo) if logo else public_resource_url("assets/logo.png"),width=85)
    with col2:
        st.markdown('<div class="abb-hero"><h1>Cálculo de Tiempo de Arranque</h1><p>Motor Start-Up Time Calculation · Evaluación térmica, arranques consecutivos y reporte técnico</p></div>',unsafe_allow_html=True)
    with col3:
        img=optional_resource("assets/motor_header.png")
        st.image(str(img) if img else public_resource_url("assets/motor_header.png"),width=95)
    if st.button("← Menú principal / Main menu",key="back_home"):
        ss["screen"]="home"
        st.rerun()


def home():
    st.markdown('<div class="abb-hero"><h1>Plataforma de Cálculos de Motores</h1><p>Motor Calculations Platform · Selección de herramienta</p></div>',unsafe_allow_html=True)
    cols=st.columns([1,3,1],vertical_alignment="center")
    with cols[0]:
        pic=optional_resource("assets/logo.png")
        st.image(str(pic) if pic else public_resource_url("assets/logo.png"),width="stretch")
    with cols[2]:
        pic=optional_resource("assets/motor_header.png")
        st.image(str(pic) if pic else public_resource_url("assets/motor_header.png"),width="stretch")
    with cols[1]:
        with st.container(border=True):
            st.markdown("### Bienvenido / Welcome")
            st.write("¿Qué tipo de cálculo quieres realizar? / What type of calculation do you want to perform?")
            st.selectbox("Herramienta / Tool",["Cálculo de Tiempo de Arranque / Start-Up Time Calculation"],key="selection")
            if st.button("Continuar / Continue",type="primary",width="stretch"):
                ss["screen"]="calculator"
                st.rerun()
            st.caption("Conserva el método original, sus fórmulas, la búsqueda MLFB, las simulaciones térmicas y el PDF.")
    st.caption("Versión Streamlit · Se elimina el comparador independiente de MLFB para mantener el alcance exclusivamente en arranque de motores.")


def excel_controls():
    with st.expander("Configuración de Archivo / File Configuration",expanded=False):
        st.caption("El Excel V46 del repositorio se consulta automáticamente al buscar un MLFB; no necesitas cargarlo. Cambiarlo es opcional.")
        x1,x2=st.columns([3,2],vertical_alignment="center")
        with x1:
            st.text_input("Archivo Excel activo",value=ss["active_excel_name"],disabled=True)
        with x2:
            st.markdown('<span class="abb-chip">Base precargada · no se exige subir archivo</span>',unsafe_allow_html=True)
        cols=st.columns(6)
        labels=[("mlfb","MLFB"),("hp","HP"),("inertia","Inercia"),("curve","Curvas"),("hot","Stall HOT"),("cold","Stall COLD")]
        for col,(key,label) in zip(cols,labels):
            with col:st.text_input(f"Col. {label}",key=f"cfg_{key}",max_chars=3)
        action=st.columns([1.5,1.5,4])
        with action[0]:
            if st.button("Guardar columnas",width="stretch"):
                new_map={k:str(ss[f"cfg_{k}"]).strip().upper() for k in DEFAULT_COLS}
                try:
                    validate_column_codes(new_map)
                    ss["current_map"]=new_map
                    ss["notice"]="Correspondencia de columnas actualizada para esta sesión."
                    st.rerun()
                except MotorDataError as exc:st.error(str(exc))
        with action[1]:
            st.button("Restaurar columnas",width="stretch",on_click=restore_column_map)
        upl=st.file_uploader("Opcional: reemplazar base Excel (.xlsx) para esta sesión",type=["xlsx"],key=f"uploaded_excel_{ss['upload_epoch']}")
        if upl is not None:
            blob=upl.getvalue()
            sha=hashlib.sha256(blob).hexdigest()
            if sha!=ss["custom_excel_hash"]:
                try:
                    if len(blob)>25*1024*1024:
                        raise MotorDataError("Archivo demasiado grande: el límite de esta app es 25 MB.")
                    report=validate_workbook_stream(blob,ss["current_map"])
                    ss["custom_excel_bytes"],ss["custom_excel_hash"]=blob,sha
                    ss["active_excel_name"],ss["source_version"]=upl.name,"Archivo sustituido en esta sesión"
                    ss["motor_found"]=False
                    st.success(f"Archivo válido: {report['mlfb_validos']} MLFB encontrados. Ahora es la base activa.")
                    st.rerun()
                except MotorDataError as exc:
                    st.error(f"No se reemplazó el Excel anterior: {exc}")
        if ss["custom_excel_bytes"] is not None:
            with st.expander("Actualizar la base oficial permanentemente (administrador)"):
                try:
                    credentials=github_settings(st.secrets)
                except Exception:
                    credentials=github_settings({})
                if credentials is None:
                    st.info("Actualización permanente opcional. Configure GITHUB_TOKEN, GITHUB_REPO y ADMIN_PASSWORD en los secretos de Streamlit para habilitarla. La subida de arriba ya funciona durante esta sesión.")
                else:
                    st.caption("Esta operación guarda el XLSX validado en el repositorio configurado. Los nuevos despliegues lo utilizarán como base oficial.")
                    st.text_input("Contraseña del administrador",type="password",key="admin_password_input")
                    if st.button("Guardar Excel como base oficial en GitHub",type="primary"):
                        if not validate_admin(ss["admin_password_input"],credentials):
                            st.error("Contraseña de administrador incorrecta.")
                        else:
                            try:
                                with st.spinner("Creando commit de la nueva base de datos..."):
                                    url=persist_to_github(ss["custom_excel_bytes"],credentials,ss["active_excel_name"])
                                st.success("Base oficial actualizada en GitHub. Los despliegues posteriores utilizarán el archivo nuevo.")
                                if url:st.link_button("Ver commit",url)
                            except PersistenceError as exc:st.error(f"No se pudo publicar el Excel: {exc}")
            if st.button("Volver al Excel original V46"):
                ss["custom_excel_bytes"]=None
                ss["custom_excel_hash"]=""
                ss["active_excel_name"]=EXCEL_NAME
                ss["source_version"]="V46 (repositorio original)"
                ss["upload_epoch"]+=1
                ss["motor_found"]=False
                st.rerun()
        st.caption("Hoja: Core Level Data 60 Hz · Encabezado: fila 3 · Las columnas se aplican en la siguiente búsqueda.")


def main():
    header()
    if ss["notice"]:
        st.success(ss["notice"])
        ss["notice"]=""
    print("[MOTOR-BOOT] Calculadora: formulario iniciado sin leer Excel", flush=True)
    st.markdown(f'<span class="abb-chip">Excel disponible: {escape(ss["active_excel_name"])} · Consulta bajo demanda</span>',unsafe_allow_html=True)
    st.write("")
    with st.container(border=True):
        section("Buscar por Código MLFB / Search by MLFB Code")
        r1,r2,r3=st.columns([5,1.3,1.4],vertical_alignment="bottom")
        with r1:
            input_field("Código MLFB (11 caracteres) / MLFB Code", "mlfb",placeholder="Ej. 1LE... (11 caracteres)")
        with r2:
            st.button("Buscar / Search",type="primary",width="stretch",
                      on_click=search_motor_callback)
        with r3:
            st.toggle("Editar datos de Excel",key="unlock_motor",help="Desbloquear los valores que se autocompletan desde la base")
        if ss.get("search_error"):
            st.error(ss["search_error"])
        if ss["motor_found"]:
            st.caption("✓ Datos cargados de Excel. Campos de motor bloqueados para proteger la referencia; puede habilitar la edición.")
    excel_controls()
    print("[MOTOR-BOOT] Calculadora: formulario MLFB y configuración listos", flush=True)

    result=calculate_motor(motor_inputs())
    print("[MOTOR-BOOT] Calculadora: motor calculado", flush=True)
    render_diagnosis(result)
    locked=ss["motor_found"] and not ss["unlock_motor"]

    left,right=st.columns(2,vertical_alignment="top")
    with left:
        with st.container(border=True):
            section("Datos del Equipo Accionado / Driven Equipment Data")
            st.checkbox("¿Es bomba o ventilador? / Is it a pump or fan?",key="is_pump",help="En el original usa automáticamente factor MMV 0.33")
            if ss["is_pump"]:
                readonly("Factor MMV (automático)",.33)
            else:
                input_field("Factor MMV (manual) / MMV Factor","factor_mmv",helptext="Introduzca factor decimal, p. ej. 0.33")
            input_field("RPM (Equipo) / Equipment RPM","rpm_eq",helptext="Revoluciones por minuto del equipo accionado")
            a,b=st.columns([2,1])
            with a:input_field("WR2 / Inercia del equipo","wr2",disabled=field_value("rpm_eq") is None)
            with b:st.selectbox("Unidad WR2",["kgm2","lbft2"],key="wr2_unit")
            a,b=st.columns([2,1])
            with a:input_field("MNV / Momento nominal","mnv",disabled=field_value("wr2") is None)
            with b:st.selectbox("Unidad MNV",["kgm","lbft"],key="mnv_unit")
            a,b=st.columns(2)
            with a:readonly("MMV (kgm)",result.values["MMV"])
            with b:readonly("JV (kgm²)",result.values["JV"])
            if field_value("rpm_eq") is None:st.caption("Paso 1: introduce RPM para habilitar WR2; después MNV.")
    with right:
        with st.container(border=True):
            section("Datos del Motor / Motor Data")
            a,b=st.columns(2)
            with a:input_field("HP (Motor)","hp",disabled=locked)
            with b:input_field("RPM (Motor)","rpm_motor",disabled=locked)
            a,b=st.columns(2)
            with a:readonly("MNM (kgm)",result.values["MNM"])
            with b:input_field("JM (kgm²)","jm",disabled=locked)
            a,b=st.columns(2)
            with a:readonly("GD2M (kgm²)",result.values["GD2M"])
            with b:readonly("MMM (kgm)",result.values["MMM"])
            a,b=st.columns(2)
            with a:input_field("Stall Time HOT (seg)","stall_hot",disabled=locked)
            with b:input_field("Stall Time COLD (seg)","stall_cold",disabled=locked)
            input_field("Factor curvas / Curve factor", "factor_curve",disabled=locked,
                        helptext="Factor BT del Excel dividido entre 100; también se puede introducir manualmente sin MLFB.")
            st.markdown("**Porcentaje de voltaje alimentado / Applied voltage (%)**")
            a,b=st.columns([4,1])
            with a:st.slider("Volts %",0,100,key="voltage_slider",label_visibility="collapsed",on_change=on_voltage_slider)
            with b:st.number_input("Volts número",min_value=0,max_value=100,step=1,key="voltage_number",label_visibility="collapsed",on_change=on_voltage_number)
            st.caption("Factor aplicado al par nominal: (voltaje / 100)²")

    # Adaptaciones exactamente en la secuencia que utiliza el formulario original.
    with st.container(border=True):
        section("Adaptaciones / Adaptations")
        maps=[("MMV nMot. (kgm)","MMV_nMot"),("GD2V (kgm²)","GD2V"),
              ("GD2V nMot. (kgm²)","GD2V_nMot"),("nGD2 (kgm²)","nGD2"),
              ("ta (segundos)","ta"),("ta CEILING (segundos)","ta_ceiling")]
        for index in range(0,len(maps),3):
            cols=st.columns(3)
            for col,(label,k) in zip(cols,maps[index:index+3]):
                with col:readonly(label,result.values[k])
        if result.warnings:
            st.warning(" · ".join(dict.fromkeys(result.warnings)))

    cons=None
    if result.values["ta"] is not None and not ss["enable_consecutive"]:
        if st.button("Activar Arranques consecutivos / Consecutive Starts",type="primary",width="stretch"):
            ss["enable_consecutive"]=True
            st.rerun()
    if ss["enable_consecutive"]:
        with st.container(border=True):
            section("Arranques consecutivos / Consecutive Starts")
            top=st.columns([5,1])
            with top[1]:
                if st.button("Ocultar módulo",width="stretch"):
                    ss["enable_consecutive"]=False
                    st.rerun()
            row=st.columns(4)
            with row[0]:input_field("f = (factor reducción)","f")
            with row[1]:input_field("GFe =", "gfe",helptext="Factor GFe utilizado en V'2A (captura manual)")
            with row[2]:input_field("Diam. rotor (dm)","rotor_diameter")
            with row[3]:input_field("Long. paquete (dm)","stack_length")
            input_field("Dibujo paquete rotor / Rotor stack drawing","drawing")
            st.radio("Tipo de estator / Stator type",["std","ranura_profunda","doble_cuadro"],
                     format_func=lambda x:{"std":"Estándar (std)","ranura_profunda":"Ranura profunda","doble_cuadro":"Doble jaula"}[x],
                     key="stator_kind",horizontal=True)
            selected_key={"std":"stator_std","ranura_profunda":"stator_deep","doble_cuadro":"stator_double"}[ss["stator_kind"]]
            selected_label={"std":"Factor estándar (std)","ranura_profunda":"Factor ranura profunda","doble_cuadro":"Factor doble jaula"}[ss["stator_kind"]]
            input_field(selected_label,selected_key,helptext="Solo se aplica el factor del tipo de estator seleccionado.")
            a,b=st.columns(2)
            with a:st.number_input("Número de arranques (frío y caliente)",min_value=1,max_value=500,step=1,key="number_starts")
            with b:st.number_input("Arranques por hora",min_value=1,max_value=500,step=1,key="starts_hour")
            cons=calculate_consecutive(result,consecutive_inputs())
            specs=[("Diamxlongitud","diamxlongitud"),("V'2A","v2a"),("V'2A Ceiling","v2a_ceiling"),
                   ("taus","taus"),("taus Ceiling","taus_ceiling"),("Taus / Ta","taus_ta"),
                   ("V2aus","v2aus"),("V2aus Ceiling","v2aus_ceiling"),
                   ("Tiempo ciclo arranque-paro","ciclo"),("Tiempo restante reposo","resto"),
                   ("Reposo por ciclo","reposo_ciclo")]
            for i in range(0,len(specs),4):
                cols=st.columns(4)
                for col,(label,key) in zip(cols,specs[i:i+4]):
                    with col:readonly(label,cons.values.get(key))
            for warning in dict.fromkeys(cons.warnings):st.warning(warning)
            section("Gráfica Arranques en Frío / Cold Starts Chart")
            st.plotly_chart(thermal_chart(cons.cold,"Temperatura por arranque en frío",TEMP_MAX_COLD),width="stretch")
            st.markdown("**Tabla Arranques en Frío / Cold Starts Table**")
            status_table(cons.cold)
            section("Gráfica Arranques en Caliente / Hot Starts Chart")
            st.plotly_chart(thermal_chart(cons.hot,"Temperatura por arranque en caliente",TEMP_MAX_HOT),width="stretch")
            st.markdown("**Tabla Arranques en Caliente / Hot Starts Table**")
            status_table(cons.hot)
            section("Arranques por Hora / Starts per Hour")
            status_table(cons.hourly,hourly=True)
            st.plotly_chart(thermal_chart(cons.hourly,"Temperatura por hora de operación",None,hourly=True),width="stretch")

    with st.container(border=True):
        section("Acciones / Actions")
        c1,c2,c3,c4=st.columns(4)
        with c1:
            st.button("↻ Reiniciar / Reset",width="stretch",on_click=reset_model)
        with c2:
            if st.button("✓ Calcular / Calculate",type="primary",width="stretch"):
                if result.values["ta"] is None:st.error("Faltan valores para calcular el tiempo de arranque; revise los campos y el factor de curvas.")
                else:st.success(f"Tiempo de arranque = {display(result.values['ta'])} s · {result.status}")
        with c3:
            if st.button("∑ Operaciones utilizadas",width="stretch"):
                operations_dialog(result,cons)
        with c4:
            if result.values["ta"] is not None:
                try:
                    pdf=generate_pdf(result,cons,ss["mlfb"],optional_resource("assets/logo.png"))
                    st.download_button("↓ Exportar PDF",pdf,
                                       file_name=f"{ss['mlfb'].strip().upper() or 'resultado_arranque'} - {date.today():%d-%m-%Y}.pdf",
                                       mime="application/pdf",type="primary",width="stretch")
                except Exception as exc:
                    st.error(f"No se pudo generar PDF: {exc}")
            else:
                st.button("↓ Exportar PDF",disabled=True,width="stretch")
        st.markdown("**Guardar / recuperar un cálculo**")
        a,b=st.columns(2)
        with a:
            st.download_button("Descargar proyecto JSON",save_project(),file_name="proyecto_motor.json",mime="application/json",width="stretch")
        with b:
            obj=st.file_uploader("Importar proyecto anterior (.json)",type=["json"],key="imported_json")
            if obj is not None:
                st.button("Cargar proyecto seleccionado",on_click=callback_import_project)
            if ss.get("import_error"):
                st.error(ss["import_error"])
    st.caption("Parámetros térmicos heredados del original. Los resultados requieren validación técnica antes de una decisión de ingeniería. ")


print(f"[MOTOR-BOOT] Renderizando pantalla: {ss['screen']}", flush=True)
if ss["screen"]=="home":home()
else:main()
print("[MOTOR-BOOT] Script ejecutado sin excepción", flush=True)
