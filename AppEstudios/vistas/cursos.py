"""Tablero y detalle de curso: autorización, formularios y respuestas HTTP."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from ..acceso import cursos_usuario, perfil, profesor_request
from ..consultas.cursos import datos_curso
from ..forms import CursoForm, NotaForm, TareaForm
from ..graficos_cursos import graficos_curso
from ..models import Estudiante
from ..periodos import periodo
from ..presentacion import SECCIONES, color, contexto
from ..servicios import (
    cerrar_semestre,
    crear_curso as guardar_curso,
    publicar_tarea,
    registrar_nota,
)


@login_required(login_url="ingresar")
def tablero(request):
    if (
        not profesor_request(request)
        and not Estudiante.objects.filter(usuario=request.user).exists()
    ):
        return redirect("mi_cuenta")
    cursos = cursos_usuario(request).order_by("asignatura", "seccion", "id")
    form = CursoForm(request.POST or None)
    if request.method == "POST":
        return crear_curso(request)
    return render(
        request,
        "portal/tablero.html",
        {
            **contexto(request, "tablero"),
            "tarjetas": [{"curso": c, "color": color(c)} for c in cursos],
            "form": form,
        },
    )


@login_required(login_url="ingresar")
def crear_curso(request):
    if not profesor_request(request):
        raise PermissionDenied
    form = CursoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        sala = guardar_curso(request.user, form)
        return redirect("curso", curso_id=sala.pk)
    return render(
        request,
        "portal/crear_curso.html",
        {
            **contexto(request, "tablero"),
            "form": form,
        },
    )


def procesar_cambio(request, sala, seccion, formularios):
    """Devuelve una redirección al guardar, o conserva el formulario con errores."""
    if not profesor_request(request) or sala.archivada:
        raise PermissionDenied
    if seccion == "calificaciones" and "crear_nota" in request.POST:
        form = NotaForm(request.POST, curso=sala)
        formularios["nota_form"] = form
        if not form.is_valid():
            return None
        try:
            registrar_nota(sala, form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
            return None
        messages.success(request, "Nota guardada en el período actual del curso.")
    elif seccion == "tareas" and "crear_tarea" in request.POST:
        form = TareaForm(request.POST)
        formularios["tarea_form"] = form
        if not form.is_valid():
            return None
        publicar_tarea(sala, form.cleaned_data)
        messages.success(
            request, "Entrega publicada para este curso, incluidos futuros inscritos."
        )
    elif seccion == "configuracion" and "terminar_semestre" in request.POST:
        try:
            cerrar_semestre(
                sala,
                request.POST.get("confirmacion", ""),
                request.POST.get("periodo_actual"),
            )
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(
                request,
                "Período cerrado. Las notas anteriores permanecen en el historial.",
            )
    else:
        raise PermissionDenied
    return redirect("curso_seccion", curso_id=sala.pk, seccion=seccion)


@login_required(login_url="ingresar")
def curso(request, curso_id, seccion="resumen", estudiante_id=None):
    sala = get_object_or_404(cursos_usuario(request), pk=curso_id)
    profesor = profesor_request(request)
    permitidas = (
        dict(SECCIONES)
        if profesor
        else {
            "resumen": "Resumen",
            "calificaciones": "Calificaciones",
            "tareas": "Tareas",
        }
    )
    if seccion not in permitidas:
        raise PermissionDenied
    estudiante = None if profesor else perfil(request)
    ficha = (
        get_object_or_404(sala.alumnos_inscritos, pk=estudiante_id)
        if estudiante_id is not None and profesor
        else None
    )
    semestre, anio = periodo(request, sala)
    formularios = {"nota_form": NotaForm(curso=sala), "tarea_form": TareaForm()}
    if request.method == "POST":
        respuesta = procesar_cambio(request, sala, seccion, formularios)
        if respuesta is not None:
            return respuesta
    datos = datos_curso(
        sala, seccion, profesor, estudiante, ficha, semestre, anio, request.GET
    )
    return render(
        request,
        "portal/curso.html",
        {
            **contexto(request, "tablero"),
            **datos,
            **formularios,
            **graficos_curso(sala, seccion, profesor, ficha, semestre, anio, datos),
            "curso": sala,
            "color": color(sala),
            "seccion": seccion,
            "plantilla_seccion": f"portal/cursos/{seccion}.html",
            "titulo_seccion": permitidas[seccion],
            "secciones": list(permitidas.items()),
            "semestre": semestre,
            "anio": anio,
            "ficha": ficha,
        },
    )
