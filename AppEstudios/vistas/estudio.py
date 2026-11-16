"""Formulario y pantalla de estudio del estudiante autenticado."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from ..acceso import perfil
from ..consultas.estudio import contexto_estudio, historial_estudio
from ..forms import RegistroEstudioForm
from ..graficos_personales import graficos_estudio
from ..presentacion import contexto
from ..servicios import guardar_total_estudio


@login_required(login_url="ingresar")
def estudio(request):
    estudiante = perfil(request)
    form = RegistroEstudioForm(
        request.POST or None,
        estudiante=estudiante,
        initial={
            "fecha": timezone.localdate(),
            "meta_semanal_minutos": estudiante.meta_semanal_minutos,
        },
    )
    if request.method == "POST" and form.is_valid():
        guardar_total_estudio(estudiante, form.cleaned_data)
        messages.success(
            request, "Total diario actualizado para ese curso. La meta es global."
        )
        return redirect("estudio")
    avance = contexto_estudio(estudiante)
    historial = historial_estudio(estudiante, request.GET)
    if historial["error_filtro"]:
        messages.error(request, historial["error_filtro"])
    return render(
        request,
        "portal/estudio.html",
        {
            **contexto(request, "estudio"),
            **avance,
            **historial,
            "form": form,
            "estudiante": estudiante,
            "charts": graficos_estudio(avance),
        },
    )
