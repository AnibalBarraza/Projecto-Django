"""Historia acotada a los estudiantes visibles y los últimos ocho períodos."""

from django.db.models import Avg, Count, Q


def historia_exploracion(curso, alumnos, semestre, anio):
    if not alumnos:
        return {}
    historia = curso.calificaciones.filter(
        Q(anio__lt=anio) | Q(anio=anio, semestre__lte=semestre)
    )
    periodos = list(
        historia.order_by("-anio", "-semestre")
        .values_list("anio", "semestre")
        .distinct()[:8]
    )
    actual = (anio, semestre)
    previo = max((p for p in periodos if p < actual), default=None)
    periodos = sorted(set(periodos + [actual]))[-8:]
    year, semester = periodos[0]
    filas = (
        historia.filter(estudiante__in=alumnos)
        .filter(Q(anio__gt=year) | Q(anio=year, semestre__gte=semester))
        .values("estudiante_id", "anio", "semestre")
        .annotate(promedio=Avg("nota"), cantidad=Count("pk"))
    )
    return {
        "periodos": periodos,
        "previo": previo,
        "valores": {(f["estudiante_id"], f["anio"], f["semestre"]): f for f in filas},
    }
