"""Generación de PDF en memoria, sin acceso a carpetas de la computadora del usuario."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from math import isfinite
import unicodedata
from fpdf import FPDF
from core.engine import MotorResult, ConsecutiveResult, display, TEMP_MAX_COLD, TEMP_MAX_HOT


def latin(value: object) -> str:
    s = str(value).replace("°", " deg").replace("²", "2").replace("≥", ">=").replace("≤", "<=")
    return unicodedata.normalize("NFKD", s).encode("latin-1", "ignore").decode("latin-1")


class MotorPDF(FPDF):
    def __init__(self, code: str, logo: Path | None = None):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.code, self.logo_path = code, logo
        self.set_margins(14, 17, 14)
        self.set_auto_page_break(True, margin=17)
        self.set_title("Calculo de tiempo de arranque de motores")
        self.set_author("Plataforma de calculos de motores")

    def header(self):
        self.set_fill_color(238, 242, 246)
        self.rect(0, 0, 210, 30, "F")
        self.set_fill_color(216, 30, 5)
        self.rect(0, 0, 5, 30, "F")
        if self.logo_path and self.logo_path.is_file():
            try:
                self.image(str(self.logo_path), x=15, y=6, w=17, h=17, keep_aspect_ratio=True)
            except Exception:
                pass
        self.set_xy(38, 7)
        self.set_font("Helvetica", "B", 13)
        self.cell(158, 8, "MOTOR START-UP CALCULATION", align="R")
        self.set_xy(38, 15)
        self.set_font("Helvetica", "", 8)
        self.cell(158, 6, latin(f"Calculo de Tiempo de Arranque  |  MLFB: {self.code or 'Manual'}"), align="R")
        self.set_y(35)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110, 119, 130)
        self.cell(0, 5, f"{datetime.now():%d/%m/%Y %H:%M}  |  Pagina {self.page_no()}", align="C")
        self.set_text_color(31, 41, 55)


def heading(pdf: FPDF, name: str):
    if pdf.get_y() > 250:
        pdf.add_page()
    pdf.set_fill_color(238, 242, 246)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 9, latin(name), new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)


def line(pdf: FPDF, label: str, value: object, unit: str = ""):
    if pdf.get_y() > 260:
        pdf.add_page()
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(122, 6, latin(label)[:72], border="B")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, latin(f"{display(value, 5)} {unit}"), border="B", new_x="LMARGIN", new_y="NEXT", align="R")


def write_table(pdf: FPDF, title: str, rows: list[dict], hourly: bool = False):
    heading(pdf, title)
    headers = ["Arr.", "Tiempo (s)" if hourly else "Temp (C)", "Temp (C)" if hourly else "Duracion (s)", "Tipo", "Estado"]
    widths = [21, 35, 34, 56, 36]
    pdf.set_fill_color(225, 230, 237)
    pdf.set_font("Helvetica", "B", 8)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1, fill=True)
    pdf.ln()
    for row in rows:
        if pdf.get_y() > 257:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(225, 230, 237)
            for h, w in zip(headers, widths):
                pdf.cell(w, 7, h, border=1, fill=True)
            pdf.ln()
        kind = row.get("estado", "OK")
        pdf.set_fill_color(*(253,236,234) if kind=="Excede" else (255,243,205) if kind=="Cerca" else (234,245,238))
        vals = [row.get("arranque", ""), display(row.get("tiempo") if hourly else row.get("temperatura")),
                display(row.get("temperatura") if hourly else row.get("segundos")),
                row.get("tipo", ""), kind]
        pdf.set_font("Helvetica", "", 8)
        for val, width in zip(vals, widths):
            pdf.cell(width, 6, latin(str(val))[:25], border=1, fill=True)
        pdf.ln()
    pdf.ln(4)


def draw_chart(pdf: FPDF, title: str, rows: list[dict], limit: float | None, hourly: bool = False):
    if not rows:
        return
    if pdf.get_y() > 170:
        pdf.add_page()
    heading(pdf, title)
    x0, y0, w, h = 25, pdf.get_y()+3, 165, 64
    values = [float(r["temperatura"]) for r in rows]
    xmax = max(float(r["tiempo"]) for r in rows) if hourly else max(1, len(rows)-1)
    ymin = min(0, min(values))
    ymax = max(max(values), limit or 0, 1) * 1.12
    spread = max(1e-6, ymax-ymin)
    if limit is not None:
        boundaries=[(0, limit*.9, (234,245,238)), (limit*.9, limit, (255,243,205)), (limit, ymax, (253,236,234))]
        for a,b,color in boundaries:
            y_a=y0+h-(max(ymin,a)-ymin)/spread*h
            y_b=y0+h-(min(ymax,b)-ymin)/spread*h
            if y_a>y_b:
                pdf.set_fill_color(*color)
                pdf.rect(x0,y_b,w,y_a-y_b,"F")
        y_limit=y0+h-(limit-ymin)/spread*h
        pdf.set_draw_color(192,0,0)
        pdf.set_dash_pattern(dash=2,gap=2)
        pdf.line(x0,y_limit,x0+w,y_limit)
        pdf.set_dash_pattern()
    pdf.set_draw_color(180,188,199)
    pdf.rect(x0,y0,w,h)
    pdf.set_font("Helvetica", "", 7)
    for i in range(5):
        yy=y0+h-(i/4)*h
        pdf.set_draw_color(225,230,235)
        pdf.line(x0,yy,x0+w,yy)
        pdf.text(x0-12,yy+2,display(ymin+(i/4)*spread,1))
    # Como en Tkinter: cortar trazo al primer exceso, pero conservar tabla completa.
    shown=[]
    for r in rows:
        shown.append(r)
        if limit is not None and r["temperatura"] >= limit:
            break
    if len(shown)==1:
        shown=rows[:2]
    pdf.set_draw_color(11,79,138)
    pdf.set_fill_color(11,79,138)
    pdf.set_line_width(.65)
    pts=[]
    for i,r in enumerate(shown):
        xvalue=float(r["tiempo"]) if hourly else i
        xx=x0+w*xvalue/max(1e-6,xmax)
        yy=y0+h-(float(r["temperatura"])-ymin)/spread*h
        pts.append((xx,yy))
    for first,second in zip(pts,pts[1:]):
        pdf.line(*first,*second)
    for xx,yy in pts:
        pdf.ellipse(xx-.7,yy-.7,1.4,1.4,"F")
    pdf.set_line_width(.2)
    pdf.set_xy(x0,y0+h+3)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(w,6,"Tiempo (s)" if hourly else "Arranques / Starts",align="C")
    pdf.set_y(y0+h+13)


def generate_pdf(motor: MotorResult, consecutive: ConsecutiveResult | None = None,
                 mlfb: str = "", logo: Path | None = None) -> bytes:
    pdf = MotorPDF(mlfb, logo)
    pdf.add_page()
    heading(pdf,"DATOS DEL MOTOR / MOTOR DATA")
    i,v=motor.inputs,motor.values
    for a,b,u in [("Potencia HP",i.hp,"HP"),("RPM motor",i.rpm_motor,"rpm"),
                  ("Voltaje alimentado",i.voltage_pct,"%"),("MNM",v["MNM"],"kgm"),
                  ("JM",i.jm,"kgm2"),("GD2M",v["GD2M"],"kgm2"),
                  ("Factor de curvas",i.factor_curve,""),("MMM",v["MMM"],"kgm"),
                  ("Stall HOT",i.stall_hot,"s"),("Stall COLD",i.stall_cold,"s")]:
        line(pdf,a,b,u)
    pdf.ln(5)
    heading(pdf,"EQUIPO ACCIONADO / DRIVEN EQUIPMENT")
    for a,b,u in [("RPM equipo",i.rpm_eq,"rpm"),("WR2 normalizado",v["WR2_normal"],"kgm2"),
                  ("MNV normalizado",v["MNV_normal"],"kgm"),("MMV",v["MMV"],"kgm"),
                  ("JV",v["JV"],"kgm2"),("MMV nMot",v["MMV_nMot"],"kgm"),
                  ("GD2V",v["GD2V"],"kgm2"),("GD2V nMot",v["GD2V_nMot"],"kgm2"),
                  ("nGD2",v["nGD2"],"kgm2"),("Tiempo de arranque",v["ta"],"s"),
                  ("Tiempo de arranque CEILING",v["ta_ceiling"],"s")]:
        line(pdf,a,b,u)
    pdf.ln(4)
    heading(pdf,"EVALUACION DE ARRANQUE / START-UP EVALUATION")
    colors={"ok":(46,125,50),"warn":(169,111,0),"bad":(192,0,0),"info":(90,105,122)}
    pdf.set_text_color(*colors.get(motor.status_kind,colors["info"]))
    pdf.set_font("Helvetica","B",11)
    pdf.multi_cell(0,7,latin(motor.status),align="C",new_x="LMARGIN",new_y="NEXT")
    pdf.set_text_color(31,41,55)
    pdf.set_font("Helvetica","",9)
    pdf.multi_cell(0,6,latin(motor.diagnosis),align="C",new_x="LMARGIN",new_y="NEXT")

    if consecutive is not None:
        pdf.add_page()
        heading(pdf,"ARRANQUES CONSECUTIVOS / CONSECUTIVE STARTS")
        for key,title,unit in [
            ("diamxlongitud","Diam x Longitud","dm2"),("v2a","V'2A","degC"),
            ("v2a_ceiling","V'2A CEILING","degC"),("taus","taus","s"),
            ("taus_ceiling","taus CEILING","s"),("taus_ta","taus / ta",""),
            ("v2aus","V2aus","degC"),("v2aus_ceiling","V2aus CEILING","degC"),
            ("ciclo","Tiempo de ciclo","s"),("resto","Tiempo restante","s"),
            ("reposo_ciclo","Reposo por ciclo","s")]:
            line(pdf,title,consecutive.values.get(key),unit)
        if consecutive.cold:
            pdf.add_page()
            write_table(pdf,"ARRANQUES EN FRIO / COLD STARTS",consecutive.cold)
            draw_chart(pdf,"GRAFICA ARRANQUES EN FRIO",consecutive.cold,TEMP_MAX_COLD)
        if consecutive.hot:
            pdf.add_page()
            write_table(pdf,"ARRANQUES EN CALIENTE / HOT STARTS",consecutive.hot)
            draw_chart(pdf,"GRAFICA ARRANQUES EN CALIENTE",consecutive.hot,TEMP_MAX_HOT)
        if consecutive.hourly:
            pdf.add_page()
            write_table(pdf,"ARRANQUES POR HORA / STARTS PER HOUR",consecutive.hourly,hourly=True)
            draw_chart(pdf,"GRAFICA ARRANQUES POR HORA",consecutive.hourly,None,hourly=True)
    return bytes(pdf.output())
