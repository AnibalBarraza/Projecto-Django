"""Operaciones de escritura: conservan invariantes y límites transaccionales."""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Calificacion, Estudiante, Materia, RegistroEstudio, Sala, Tarea


def crear_curso(usuario, formulario):
    curso = formulario.save(commit=False)
    curso.profesor = usuario
    curso.nombre_profesor = usuario.get_full_name() or usuario.username
    curso.semestre_inicio = curso.semestre_actual
    curso.anio_inicio = curso.anio_actual
    curso.save()
    return curso


@transaction.atomic
def registrar_nota(curso, datos):
    actual = Sala.objects.select_for_update().get(pk=curso.pk)
    if actual.archivada:
        raise ValidationError("El curso está archivado.")
    materia, _ = Materia.objects.get_or_create(nombre=actual.asignatura)
    return Calificacion.objects.create(
        sala=actual,
        materia=materia,
        estudiante=datos["estudiante"],
        nota=datos["nota"],
        tipo_evaluacion=datos["tipo_evaluacion"],
        semestre=actual.semestre_actual,
        anio=actual.anio_actual,
    )


def publicar_tarea(curso, datos):
    materia, _ = Materia.objects.get_or_create(nombre=curso.asignatura)
    return Tarea.objects.create(sala=curso, materia=materia, estudiante=None, **datos)


@transaction.atomic
def cerrar_semestre(curso, confirmacion, periodo_esperado):
    if confirmacion.strip().casefold() != "si":
        raise ValidationError("Escribe SI para confirmar el cierre.")
    actual = Sala.objects.select_for_update().get(pk=curso.pk)
    if actual.archivada:
        raise ValidationError("El curso está archivado.")
    if periodo_esperado != f"{actual.semestre_actual}-{actual.anio_actual}":
        raise ValidationError(
            "El período ya cambió. Revisa el curso antes de cerrar nuevamente."
        )
    actual.semestre_actual = 2 if actual.semestre_actual == 1 else 1
    if actual.semestre_actual == 1:
        actual.anio_actual += 1
    actual.save(update_fields=["semestre_actual", "anio_actual"])


@transaction.atomic
def guardar_total_estudio(estudiante, datos):
    # Serializa las actualizaciones del mismo estudiante, además de la unicidad SQL.
    Estudiante.objects.select_for_update().get(pk=estudiante.pk)
    RegistroEstudio.objects.update_or_create(
        estudiante=estudiante,
        fecha=datos["fecha"],
        sala=datos["sala"],
        defaults={"minutos": datos["minutos"]},
    )
    estudiante.meta_semanal_minutos = datos["meta_semanal_minutos"]
    estudiante.save(update_fields=["meta_semanal_minutos"])
