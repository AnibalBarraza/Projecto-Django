"""Selección de semestre y año, independiente del estado de sesión."""

from django.utils import timezone


def periodo(request, curso=None):
    hoy = timezone.localdate()
    try:
        semestre = int(
            request.GET.get(
                "semestre",
                curso.semestre_actual if curso else (1 if hoy.month <= 6 else 2),
            )
        )
        anio = int(request.GET.get("anio", curso.anio_actual if curso else hoy.year))
        if semestre not in (1, 2) or not 1900 <= anio <= 2200:
            raise ValueError
    except (ValueError, TypeError):
        semestre, anio = (
            (curso.semestre_actual, curso.anio_actual)
            if curso
            else (1 if hoy.month <= 6 else 2, hoy.year)
        )
    return semestre, anio
