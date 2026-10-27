from django.contrib import admin
from .models import Estudiante, Materia, Calificacion, Tarea

@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'edad', 'tiempo_viaje')
    search_fields = ('nombre',)

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'materia', 'semestre', 'nota')
    list_filter = ('materia', 'semestre')

@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'estudiante', 'materia', 'fecha_entrega', 'completada')
    list_filter = ('completada', 'materia')
