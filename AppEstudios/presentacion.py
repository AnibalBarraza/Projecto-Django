"""Colores y navegación compartidos por las pantallas activas."""

from .acceso import profesor_request

COLORS = ["#245bb5", "#0f766e", "#9341a4", "#b45309", "#b83e5c", "#426331"]
SECCIONES = [
    ("resumen", "Resumen"),
    ("estudiantes", "Estudiantes"),
    ("calificaciones", "Calificaciones"),
    ("habitos", "Hábitos de estudio"),
    ("tareas", "Tareas"),
    ("configuracion", "Configuración"),
]


def color(curso):
    return COLORS[(curso.pk - 1) % len(COLORS)]


def contexto(request, activo):
    return {
        "profesor": profesor_request(request),
        "activo": activo,
    }
