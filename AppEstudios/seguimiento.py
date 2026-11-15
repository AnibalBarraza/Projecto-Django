from datetime import timedelta

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import RegistroEstudioForm
from .models import Estudiante, RegistroEstudio


def contexto_estudio(estudiante):
    hoy = timezone.localdate()
    lunes = hoy - timedelta(days=hoy.weekday())

    registros = estudiante.registros_estudio.filter(
        fecha__range=(lunes, hoy)
    )
    minutos = registros.aggregate(total=Sum("minutos"))["total"] or 0
    meta = estudiante.meta_semanal_minutos
    progreso = min(100, round(minutos * 100 / max(meta, 1)))

    if not registros.exists():
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
        "formulario_estudio": RegistroEstudioForm(
            initial={
                "fecha": hoy,
                "meta_semanal_minutos": meta,
            }
        ),
        "minutos_semana": minutos,
        "progreso_meta": progreso,
        "consejo_estudio": consejo,
        "registros_recientes": estudiante.registros_estudio.all()[:7],
    }


@require_POST
def guardar_estudio(request):
    estudiante = Estudiante.objects.filter(
        id=request.session.get("estudiante_id")
    ).first()

    if not estudiante:
        return redirect("usuario")

    formulario = RegistroEstudioForm(request.POST)

    if not formulario.is_valid():
        return render(
            request,
            "registro_estudio_error.html",
            {"formulario_estudio": formulario},
            status=400,
        )

    datos = formulario.cleaned_data

    RegistroEstudio.objects.update_or_create(
        estudiante=estudiante,
        fecha=datos["fecha"],
        defaults={"minutos": datos["minutos"]},
    )

    estudiante.meta_semanal_minutos = datos["meta_semanal_minutos"]
    estudiante.save(update_fields=["meta_semanal_minutos"])

    messages.success(
        request,
        "Registro guardado. Si esa fecha ya existía, actualizamos su total.",
    )
    return redirect("usuario")