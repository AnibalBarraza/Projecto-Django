"""Consulta de rendimiento general de los cursos visibles para la cuenta."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ..acceso import cursos_usuario, perfil, profesor_request
from ..consultas.rendimiento import datos_rendimiento
from ..graficos_personales import graficos_rendimiento
from ..periodos import periodo
from ..presentacion import contexto


@login_required(login_url="ingresar")
def rendimiento(request):
    cursos = list(cursos_usuario(request).order_by("asignatura", "seccion"))
    semestre, anio = periodo(request)
    estudiante = None if profesor_request(request) else perfil(request)
    datos = datos_rendimiento(cursos, estudiante, semestre, anio)
    return render(
        request,
        "portal/rendimiento.html",
        {
            **contexto(request, "rendimiento"),
            **datos,
            "semestre": semestre,
            "anio": anio,
            "charts": graficos_rendimiento(datos, semestre, anio),
        },
    )
