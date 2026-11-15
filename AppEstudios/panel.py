from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from .models import Calificacion, RegistroEstudio, Tarea


def datos_panel(sala, semestre, anio):
    estudiantes = list(
        sala.estudiantes.order_by("apellido", "nombre")
    )

    notas = list(
        Calificacion.objects
        .filter(estudiante__sala=sala)
        .select_related("materia", "estudiante")
        .order_by("anio", "semestre", "id")
    )

    por_estudiante = defaultdict(list)
    por_periodo = defaultdict(list)

    for nota in notas:
        por_estudiante[nota.estudiante_id].append(nota)
        por_periodo[(nota.anio, nota.semestre)].append(nota)

    hoy = timezone.localdate()
    lunes = hoy - timedelta(days=hoy.weekday())

    minutos = defaultdict(int)

    registros = RegistroEstudio.objects.filter(
        estudiante__sala=sala,
        fecha__range=(lunes, hoy),
    )

    for registro in registros:
        minutos[registro.estudiante_id] += registro.minutos

    rangos = [
        "Menor a 4,0",
        "Desde 4,0 a menos de 5,0",
        "Desde 5,0 a menos de 6,0",
        "Desde 6,0 a 7,0",
        "Sin notas",
    ]

    filas = []

    for estudiante in estudiantes:
        actuales = [
            nota
            for nota in por_estudiante[estudiante.id]
            if (nota.semestre, nota.anio) == (semestre, anio)
        ]

        promedio = (
            sum(nota.nota for nota in actuales) / len(actuales)
            if actuales else None
        )

        if promedio is None:
            grupo = 4
        elif promedio < 4:
            grupo = 0
        elif promedio < 5:
            grupo = 1
        elif promedio < 6:
            grupo = 2
        else:
            grupo = 3

        filas.append({
            "estudiante": estudiante,
            "promedio": promedio,
            "grupo": grupo,
            "notas": actuales,
            "minutos": minutos.get(estudiante.id),
            "registros": estudiante.registros_estudio.all()[:7],
        })

    periodos = []

    for (year, term), valores in sorted(por_periodo.items()):
        periodos.append({
            "label": f"Semestre {term} · {year}",
            "promedio": sum(n.nota for n in valores) / len(valores),
            "notas": valores,
        })

    notas_seleccionadas = [
        nota for fila in filas for nota in fila["notas"]
    ]

    return {
        "panel_filas": filas,
        "panel_periodos": periodos,
        "panel_rangos": rangos,
        "panel_distribucion": [
            sum(fila["grupo"] == i for fila in filas)
            for i in range(5)
        ],
        "panel_evolucion_labels": [
            periodo["label"] for periodo in periodos
        ],
        "panel_evolucion_data": [
            round(periodo["promedio"], 2)
            for periodo in periodos
        ],
        "panel_tareas": (
            Tarea.objects
            .filter(estudiante__sala=sala)
            .select_related("estudiante")
            .order_by("fecha_entrega")
        ),
        "panel_promedio": (
            sum(n.nota for n in notas_seleccionadas)
            / len(notas_seleccionadas)
            if notas_seleccionadas else None
        ),
    }