"""Promedios por curso y período, con el mismo peso para cada curso."""

from collections import defaultdict
from django.db.models import Avg
from ..models import Calificacion
from ..presentacion import color


def datos_rendimiento(cursos, estudiante, semestre, anio):
    notas = Calificacion.objects.filter(sala__in=cursos)
    if estudiante is not None:
        notas = notas.filter(estudiante=estudiante)
    # One grouped query for all courses and periods, independent of history length.
    agregados = list(
        notas.values("sala_id", "semestre", "anio")
        .annotate(promedio=Avg("nota"))
        .order_by("anio", "semestre", "sala_id")
    )
    medias = {
        r["sala_id"]: r["promedio"]
        for r in agregados
        if (r["semestre"], r["anio"]) == (semestre, anio)
    }
    filas = [
        {"curso": c, "promedio": medias.get(c.pk), "color": color(c)} for c in cursos
    ]
    periodos = defaultdict(list)
    for r in agregados:
        periodos[(r["semestre"], r["anio"])].append(r["promedio"])
    evolucion = [
        {"semestre": s, "anio": a, "promedio": sum(valores) / len(valores)}
        for (s, a), valores in periodos.items()
    ]
    return {
        "filas": filas,
        "total_cursos": len(cursos),
        "cursos_con_notas": len(medias),
        "evolucion": evolucion,
        "promedio_general": sum(medias.values()) / len(medias) if medias else None,
    }
