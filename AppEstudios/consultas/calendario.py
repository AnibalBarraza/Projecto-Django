"""Entregas autorizadas y estructura del mes; no depende de la sesión HTTP."""

import calendar
from datetime import date, timedelta
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from ..models import Tarea
from ..presentacion import color


def datos_calendario(cursos, profesor, estudiante, parametros):
    tareas = Tarea.objects.filter(sala__in=cursos).select_related("sala", "materia")
    if not profesor:
        tareas = tareas.filter(Q(estudiante=estudiante) | Q(estudiante__isnull=True))
    filtro = parametros.get("curso", "")
    if filtro:
        elegido = (
            next((c for c in cursos if c.pk == int(filtro)), None)
            if filtro.isdecimal()
            else None
        )
        if elegido is None:
            raise Http404("Curso no disponible.")
        tareas = tareas.filter(sala=elegido)
    hoy = timezone.localdate()
    try:
        inicio = date(
            int(parametros.get("anio", hoy.year)),
            int(parametros.get("mes", hoy.month)),
            1,
        )
        if not 1900 <= inicio.year <= 2200:
            raise ValueError
    except (ValueError, TypeError):
        inicio = hoy.replace(day=1)
    fin = inicio.replace(day=calendar.monthrange(inicio.year, inicio.month)[1])
    eventos, vistos = {}, set()
    for t in tareas.filter(fecha_entrega__range=(inicio, fin)).order_by(
        "fecha_entrega", "titulo", "pk"
    ):
        clave = (t.sala_id, t.titulo, t.fecha_entrega, t.materia_id)
        if clave in vistos:
            continue
        vistos.add(clave)
        eventos.setdefault(t.fecha_entrega, []).append(
            {"tarea": t, "color": color(t.sala)}
        )
    semanas = [
        [
            {
                "fecha": d,
                "eventos": eventos.get(d, []),
                "actual": d.month == inicio.month,
            }
            for d in semana
        ]
        for semana in calendar.Calendar().monthdatescalendar(inicio.year, inicio.month)
    ]
    return {
        "cursos": cursos,
        "filtro": filtro,
        "inicio": inicio,
        "anterior": inicio - timedelta(days=1),
        "siguiente": fin + timedelta(days=1),
        "semanas": semanas,
        "agenda": [{"fecha": d, "eventos": e} for d, e in sorted(eventos.items())],
    }
