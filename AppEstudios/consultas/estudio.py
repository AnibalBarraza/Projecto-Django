"""Historial de estudio filtrado y paginado exclusivamente para su dueño."""

from datetime import date, timedelta
from urllib.parse import urlencode
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ..paginacion import navegacion, paginar


def historial_estudio(estudiante, parametros):
    error = None
    historial = estudiante.registros_estudio.select_related("sala").order_by(
        "-fecha", "-pk"
    )
    filtros = {}
    fecha = parametros.get("fecha", "")
    if fecha:
        try:
            filtros["fecha"] = date.fromisoformat(fecha)
            historial = historial.filter(fecha=filtros["fecha"])
        except ValueError:
            error = "La fecha del filtro no es válida."
    curso_filtro = parametros.get("curso", "")
    if curso_filtro == "general":
        historial = historial.filter(sala__isnull=True)
        filtros["curso"] = curso_filtro
    elif curso_filtro:
        sala_filtro = (
            get_object_or_404(estudiante.cursos, pk=curso_filtro)
            if curso_filtro.isdecimal()
            else None
        )
        if sala_filtro is None:
            raise PermissionDenied
        historial = historial.filter(sala=sala_filtro)
        filtros["curso"] = curso_filtro
    pagina = paginar(historial, parametros)
    return {
        "historial": pagina,
        "filtros": filtros,
        "filtros_query": urlencode(filtros),
        "paginacion_historial": navegacion(pagina, parametros, ancla="historial"),
        "error_filtro": error,
    }


def contexto_estudio(estudiante):
    hoy = timezone.localdate()
    lunes = hoy - timedelta(days=hoy.weekday())

    desde = lunes - timedelta(weeks=3)
    recientes = list(
        estudiante.registros_estudio.filter(fecha__range=(desde, hoy)).select_related(
            "sala"
        )
    )
    registros = [r for r in recientes if r.fecha >= lunes]
    minutos = sum(r.minutos for r in registros)
    meta = estudiante.meta_semanal_minutos
    progreso = min(100, round(minutos * 100 / max(meta, 1)))

    if not registros:
        consejo = (
            "Comienza registrando tu estudio de hoy. Prueba un bloque "
            "de 25 minutos con una pausa breve."
        )
    elif minutos < meta:
        consejo = (
            "Distribuye el tiempo que falta para tu meta durante la semana. "
            "Elige una tarea concreta para cada bloque de estudio."
        )
    else:
        consejo = (
            "Alcanzaste tu meta semanal. Practica con ejercicios para "
            "revisar lo aprendido y mantén espacios de descanso."
        )

    return {
        "minutos_semana": minutos,
        "registros_semana": registros,
        "registros_mes": recientes,
        "desde": desde,
        "lunes": lunes,
        "hoy": hoy,
        "progreso_meta": progreso,
        "consejo_estudio": consejo,
    }
