"""Gráficos del curso construidos con datos ya autorizados y consultados."""

from urllib.parse import urlencode

from django.urls import reverse

from .graficos import grafico, punto
from .presentacion import color


def graficos_curso(curso, seccion, profesor, ficha, semestre, anio, datos):
    query = urlencode({"semestre": semestre, "anio": anio})
    url_notas = (
        reverse("curso_seccion", args=[curso.pk, "calificaciones"]) + "?" + query
    )
    charts = []
    periodo = f"Semestre {semestre} · {anio}"
    if profesor and seccion == "calificaciones":
        charts.append(
            grafico(
                "distribucion",
                "Distribución de promedios",
                periodo,
                "estudiantes",
                [
                    punto(
                        r["label"],
                        len(r["alumnos"]),
                        url_notas + "&banda=" + str(i) + "#seleccion",
                        (
                            color(curso)
                            if datos["banda_seleccionada"] in (None, i)
                            else "#d8dce9"
                        ),
                    )
                    for i, r in enumerate(datos["histograma"])
                ],
                ayuda="Cada columna cuenta estudiantes, no notas. Selecciona un rango para explorar sus fichas.",
                tipo="histograma",
            )
        )
        rango = datos["rango_label"]
        charts.append(
            grafico(
                "estudiantes",
                "Promedios por estudiante",
                periodo + (f" · Rango {rango}" if rango else ""),
                "nota",
                [
                    punto(
                        f"{a.nombre} {a.apellido}",
                        datos["promedios"][a.pk],
                        reverse("ficha_estudiante", args=[curso.pk, a.pk])
                        + "?"
                        + query,
                        color(curso),
                    )
                    for a in datos["alumnos_grafico"]
                ],
                maximo=7,
                ayuda="Cada punto representa un estudiante. Selecciónalo para ver sus notas. Hasta 30 por página.",
                tipo="puntos",
                orientacion="horizontal",
                referencia=4,
            )
        )
    if seccion == "calificaciones" and not profesor or ficha is not None:
        charts.append(
            grafico(
                "notas",
                "Notas del período",
                periodo,
                "nota",
                [
                    punto(
                        f"Nota {datos['inicio_notas'] + i + 1}",
                        n.nota,
                        "#detalle-" + str(n.pk),
                        color(curso),
                    )
                    for i, n in enumerate(datos["notas"])
                ],
                maximo=7,
                ayuda="Cada punto es una nota. Selecciónalo para abrir su detalle. Orden de registro; no representa fechas de evaluación.",
                tipo="puntos",
                orientacion="horizontal" if len(datos["notas"]) == 1 else "vertical",
                referencia=4,
                offset=datos["inicio_notas"],
            )
        )
    evolucion = datos["evolucion"]
    if len(evolucion) > 1:
        charts.append(
            grafico(
                "historia-curso",
                (
                    "Evolución del curso"
                    if profesor and ficha is None
                    else "Evolución por semestre"
                ),
                "Historial por semestre y año",
                "nota",
                [
                    punto(
                        f"S{e['semestre']} · {e['anio']}",
                        e["promedio"],
                        (
                            reverse("ficha_estudiante", args=[curso.pk, ficha.pk])
                            if ficha
                            else reverse(
                                "curso_seccion", args=[curso.pk, "calificaciones"]
                            )
                        )
                        + "?"
                        + urlencode({"semestre": e["semestre"], "anio": e["anio"]}),
                        color(curso),
                    )
                    for e in evolucion
                ],
                maximo=7,
                tipo="linea",
                ayuda="Selecciona un período para abrir sus calificaciones.",
            )
        )
    if seccion == "habitos":
        charts.append(
            grafico(
                "habitos",
                "Estudio registrado por estudiante",
                f"{datos['lunes']:%d/%m/%Y} al {datos['hoy']:%d/%m/%Y}",
                "minutos",
                [
                    punto(
                        f"{h['alumno'].nombre} {h['alumno'].apellido}",
                        h["minutos"],
                        "#habito-" + str(h["alumno"].pk),
                        color(curso),
                    )
                    for h in datos["habitos"]
                    if h["minutos"] is not None
                ],
                ayuda="Estudiantes de la página actual. Selecciona una barra para ver su fila; sin registro no significa cero minutos de estudio real.",
            )
        )
    if profesor and seccion == "resumen":
        url_alumnos = reverse("curso_seccion", args=[curso.pk, "estudiantes"])
        charts.append(
            grafico(
                "edades",
                "Edades del curso",
                "Estudiantes inscritos actualmente",
                "estudiantes",
                [
                    punto(
                        str(f["edad"]) + " años",
                        f["total"],
                        url_alumnos + "?" + urlencode({"edad": f["edad"]}),
                        color(curso),
                    )
                    for f in datos["edades"]
                ],
                tipo="columnas",
                ayuda="Selecciona una edad para ver los estudiantes. Describe el curso; no mide riesgo académico.",
            )
        )
        charts.append(
            grafico(
                "viajes",
                "Tiempo de viaje",
                "Estudiantes inscritos actualmente",
                "estudiantes",
                [
                    punto(
                        f["tiempo_viaje"],
                        f["total"],
                        url_alumnos + "?" + urlencode({"viaje": f["tiempo_viaje"]}),
                        color(curso),
                    )
                    for f in datos["viajes"]
                ],
                ayuda="Selecciona un tramo para explorar sus estudiantes. No se infiere que el viaje cause un resultado académico.",
            )
        )
    return {"charts": charts, "url_notas": url_notas}
