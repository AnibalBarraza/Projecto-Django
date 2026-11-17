"""Página pública de presentación, independiente del tablero autenticado."""

from django.shortcuts import render
from django.views.decorators.http import require_safe


@require_safe
def inicio(request):
    return render(request, "inicio.html")
