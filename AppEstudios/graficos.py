"""Presentation data for local, accessible SVG charts (no external requests)."""

from math import ceil


def punto(label, valor, url, color):
    return {"label": label, "value": float(valor), "url": url, "color": color}


def grafico(
    clave,
    titulo,
    periodo,
    unidad,
    puntos,
    maximo=None,
    tipo="barras",
    ayuda="",
    **opciones
):
    escala = maximo or max((p["value"] for p in puntos), default=1) or 1
    if unidad in ("estudiantes", "minutos"):
        escala = max(4, ceil(escala / 4) * 4)
    return {
        "id": clave,
        "title": titulo,
        "period": periodo,
        "unit": unidad,
        "points": puntos,
        "max": escala,
        "type": tipo,
        "help": ayuda,
        **opciones,
    }
