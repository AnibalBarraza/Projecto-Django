"""Calendario de las entregas visibles para el usuario autenticado."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from ..acceso import cursos_usuario, perfil, profesor_request
from ..consultas.calendario import datos_calendario
from ..presentacion import contexto


@login_required(login_url="ingresar")
def calendario(request):
    cursos = list(cursos_usuario(request).order_by("asignatura", "seccion"))
    profesor = profesor_request(request)
    estudiante = None if profesor else perfil(request)
    return render(
        request,
        "portal/calendario.html",
        {
            **contexto(request, "calendario"),
            **datos_calendario(cursos, profesor, estudiante, request.GET),
        },
    )
