"""Gráficas con bandas de evaluación como los Canvas originales de Tkinter."""
from __future__ import annotations
import plotly.graph_objects as go
from core.engine import TEMP_MAX_COLD, TEMP_MAX_HOT


def thermal_chart(rows: list[dict], title: str, limit: float | None, hourly=False):
    fig=go.Figure()
    fig.update_layout(
        height=290, margin=dict(l=40,r=14,t=38,b=35),
        paper_bgcolor="#ffffff",plot_bgcolor="#ffffff",
        font=dict(family="Arial",size=11,color="#334155"),
        title=dict(text=title,font=dict(size=14)),
        xaxis=dict(title="Tiempo (seg)" if hourly else "Arranques / puntos de simulación",showgrid=True,gridcolor="#e7edf4"),
        yaxis=dict(title="Temperatura (°C)",showgrid=True,gridcolor="#e7edf4"),
        showlegend=False, hovermode="x unified",
    )
    if not rows:
        fig.add_annotation(text="Complete todos los datos para mostrar la gráfica.", xref="paper",yref="paper",x=.5,y=.5,showarrow=False)
        return fig
    temperatures=[row["temperatura"] for row in rows]
    upper=max(max(temperatures),limit or 0,1)*1.13
    if limit is not None:
        fig.add_hrect(y0=0,y1=limit*.9,fillcolor="#eaf5ee",opacity=.82,line_width=0,layer="below")
        fig.add_hrect(y0=limit*.9,y1=limit,fillcolor="#fff3cd",opacity=.82,line_width=0,layer="below")
        fig.add_hrect(y0=limit,y1=upper,fillcolor="#fdecea",opacity=.82,line_width=0,layer="below")
        fig.add_hline(y=limit,line_dash="dash",line_color="#c00000",annotation_text=f"Límite {limit:g} °C",annotation_position="top left")
    visible=[]
    for row in rows:
        visible.append(row)
        if limit is not None and row["temperatura"]>=limit:
            break
    if len(visible)==1:
        visible=rows[:2]
    x=[r["tiempo"] if hourly else k+1 for k,r in enumerate(visible)]
    y=[r["temperatura"] for r in visible]
    fig.add_trace(go.Scatter(x=x,y=y,mode="lines+markers",line=dict(color="#0b4f8a",width=3),
                             marker=dict(size=6,color="#0b4f8a"),name="Temperatura",
                             hovertemplate="Punto: %{x}<br>Temperatura: %{y:.3f} °C<extra></extra>"))
    fig.update_yaxes(range=[min(0,min(temperatures)),upper])
    return fig
