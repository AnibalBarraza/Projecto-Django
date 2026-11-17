"""Entradas HTTP públicas; la implementación se organiza por área en vistas/."""

from .vistas.calendario import calendario
from .vistas.cursos import crear_curso, curso, tablero
from .vistas.estudio import estudio
from .vistas.rendimiento import rendimiento

from .vistas.inicio import inicio
