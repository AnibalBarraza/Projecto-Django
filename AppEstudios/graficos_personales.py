"""Gráficos generales y de estudio a partir de conjuntos ya autorizados."""

from collections import defaultdict
from datetime import timedelta
from urllib.parse import urlencode
from django.urls import reverse
from .graficos import grafico, punto
from .presentacion import color


def graficos_rendimiento(datos, semestre, anio):
    charts = [
        grafico(
            "cursos",
            "Promedio por curso",
            f"Semestre {semestre} · {anio}",
            "nota",
            [
                punto(
                    f"{f['curso'].asignatura} {f['curso'].seccion}".strip(),
                    f["promedio"],
                    reverse("curso_seccion", args=[f["curso"].pk, "calificaciones"])
                    + "?"
                    + urlencode({"semestre": semestre, "anio": anio}),
                    f["color"],
                )
                for f in datos["filas"]
                if f["promedio"] is not None
            ],
            maximo=7,
            ayuda="Selecciona un curso para explorar su distribución y estudiantes, o tus notas si eres estudiante.",
        )
    ]
    if len(datos["evolucion"]) > 1:
        charts.append(
            grafico(
                "evolucion",
                "Evolución del rendimiento",
                "Historial por semestre y año · cada curso pesa lo mismo",
                "nota",
                [
                    punto(
                        f"S{p['semestre']} · {p['anio']}",
                        p["promedio"],
                        "?" + urlencode({"semestre": p["semestre"], "anio": p["anio"]}),
                        "#245bb5",
                    )
                    for p in datos["evolucion"]
                ],
                maximo=7,
                tipo="linea",
                ayuda="Selecciona un punto para ver los cursos de ese período y continuar a sus calificaciones.",
            )
        )
    return charts


def graficos_estudio(avance):
    registros = avance["registros_semana"]
    diarios, por_curso, nombres, colores = defaultdict(int), defaultdict(int), {}, {}
    for r in registros:
        diarios[r.fecha] += r.minutos
        clave = str(r.sala_id) if r.sala_id else "general"
        por_curso[clave] += r.minutos
        nombres[clave] = (
            f"{r.sala.asignatura} {r.sala.seccion}".strip()
            if r.sala
            else "Estudio general"
        )
        colores[clave] = color(r.sala) if r.sala else "#54647a"
    dias = [
        avance["lunes"] + timedelta(days=i)
        for i in range((avance["hoy"] - avance["lunes"]).days + 1)
    ]
    charts = [
        grafico(
            "estudio-dias",
            "Estudio de esta semana",
            f"{avance['lunes']:%d/%m/%Y} al {avance['hoy']:%d/%m/%Y}",
            "minutos",
            (
                [
                    punto(
                        d.strftime("%d/%m"),
                        diarios[d],
                        "?fecha=" + d.isoformat() + "#historial",
                        "#245bb5",
                    )
                    for d in dias
                ]
                if registros
                else []
            ),
            tipo="columnas",
            ayuda="Selecciona un día para ver sus registros. Cero indica que no hay minutos registrados, no ausencia de estudio real.",
        ),
        grafico(
            "estudio-cursos",
            "Distribución del estudio",
            "Semana actual",
            "minutos",
            [
                punto(nombres[k], v, "?curso=" + k + "#historial", colores[k])
                for k, v in por_curso.items()
            ],
            tipo=(
                "anillo"
                if len(por_curso) > 1 and sum(por_curso.values()) > 0
                else "barras"
            ),
            ayuda="Selecciona un curso o Estudio general para consultar su historial. Cada registro se suma una vez.",
        ),
    ]
    por_fecha = defaultdict(int)
    for r in avance["registros_mes"]:
        por_fecha[r.fecha] += r.minutos
    celdas = []
    for i in range((avance["hoy"] - avance["desde"]).days + 1):
        dia = avance["desde"] + timedelta(days=i)
        celda = punto(
            dia.strftime("%d/%m/%Y"),
            por_fecha[dia],
            "?fecha=" + dia.isoformat() + "#historial",
            "#635bff",
        )
        celda.update({"row": i // 7, "column": dia.weekday()})
        celdas.append(celda)
    charts.append(
        grafico(
            "constancia",
            "Estudio registrado en las últimas cuatro semanas",
            f"{avance['desde']:%d/%m/%Y} al {avance['hoy']:%d/%m/%Y}",
            "minutos",
            celdas if avance["registros_mes"] else [],
            tipo="calor",
            ayuda="El color representa minutos registrados. Selecciona un día para consultar su historial; una celda vacía no prueba que no estudiaste.",
            columns=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
            rows=["Semana " + str(i + 1) for i in range(4)],
        )
    )
    return charts
