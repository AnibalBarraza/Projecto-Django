"""Permisos por petición y cursos visibles para la cuenta autenticada."""

from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from .models import Estudiante, Sala


def es_profesor(usuario):
    return usuario.is_authenticated and (
        usuario.is_superuser or usuario.groups.filter(name="Profesores").exists()
    )


def profesor_request(request):
    if not hasattr(request, "_portal_profesor"):
        request._portal_profesor = es_profesor(request.user)
    return request._portal_profesor


def perfil(request):
    if profesor_request(request):
        raise PermissionDenied(
            "Utiliza una cuenta de estudiante para acceder a este espacio."
        )
    if not hasattr(request, "_portal_estudiante"):
        request._portal_estudiante = get_object_or_404(Estudiante, usuario=request.user)
    return request._portal_estudiante


def cursos_usuario(request):
    if profesor_request(request):
        return Sala.objects.filter(profesor=request.user)
    return perfil(request).cursos.all()
