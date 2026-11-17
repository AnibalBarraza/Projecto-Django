"""Exploración académica por estudiante, con retorno a filtros locales."""

from urllib.parse import parse_qsl, urlencode

from django.urls import reverse

from .graficos import grafico, punto
from .presentacion import color

CAMPOS_RETORNO = {
    "semestre",
    "anio",
    "banda",
    "rango",
    "pagina_estudiantes",
    "pagina",
    "edad",
    "viaje",
}


def filtros_retorno(parametros):
    return urlencode({k: v for k, v in parametros.items() if k in CAMPOS_RETORNO})


def enlace_ficha(curso, alumno, semestre, anio, parametros):
    return (
        reverse("ficha_estudiante", args=[curso.pk, alumno.pk])
        + "?"
        + urlencode(
            {
                "semestre": semestre,
                "anio": anio,
                "volver": parametros.get("volver", filtros_retorno(parametros)),
            }
        )
    )


def contexto_exploracion(curso, ficha, semestre, anio, parametros):
    if ficha is None:
        return {}
    filtros = {
        k: v for k, v in parse_qsl(parametros.get("volver", "")) if k in CAMPOS_RETORNO
    }
    filtros.setdefault("semestre", semestre)
    filtros.setdefault("anio", anio)
    return {
        "url_volver": reverse("curso_seccion", args=[curso.pk, "calificaciones"])
        + "?"
        + urlencode(filtros)
        + "#estudiantes-grafico"
    }


def graficos_exploracion(curso, datos, ficha, semestre, anio, parametros):
    alumnos = [ficha] if ficha else datos.get("alumnos_exploracion", [])
    if not alumnos:
        return []
    # Períodos hasta el seleccionado, sin inventar semestres intermedios.
    historia = datos["historia_exploracion"]
    periodos = historia["periodos"]
    previo = historia["previo"]
    valores = historia["valores"]
    tono = color(curso)
    charts = []
    if not ficha:
        celdas = []
        for r, alumno in enumerate(alumnos):
            for c, (year, semester) in enumerate(periodos):
                fila = valores.get((alumno.pk, year, semester))
                celda = punto(
                    f"{alumno.nombre} {alumno.apellido} · S{semester} {year}",
                    fila["promedio"] if fila else 0,
                    enlace_ficha(curso, alumno, semester, year, parametros),
                    tono,
                )
                celda.update(
                    row=r,
                    column=c,
                    missing=fila is None,
                    display=(
                        f'{fila["promedio"]:.2f}'.replace(".", ",") if fila else "—"
                    ),
                )
                celdas.append(celda)
        charts.append(
            grafico(
                "historia-estudiantes",
                "Mapa de promedios por semestre",
                "Hasta el período seleccionado · últimos 8 períodos",
                "nota",
                celdas,
                maximo=7,
                tipo="matriz",
                rows=[f"{a.nombre} {a.apellido}" for a in alumnos],
                columns=[f"S{s} · {y}" for y, s in periodos],
                ayuda="Cada celda abre la ficha en ese período. — significa sin notas, no una nota cero. Estudiantes de la página y rango seleccionados.",
            )
        )
        puntos = []
        for alumno in alumnos:
            fila = valores.get((alumno.pk, anio, semestre))
            if fila:
                p = punto(
                    f"{alumno.nombre} {alumno.apellido}",
                    fila["promedio"],
                    enlace_ficha(curso, alumno, semestre, anio, parametros),
                    tono,
                )
                p.update(
                    x=fila["cantidad"], detail=f'{fila["cantidad"]} notas registradas'
                )
                puntos.append(p)
        charts.append(
            grafico(
                "promedio-cantidad",
                "Promedio y cantidad de notas",
                f"Semestre {semestre} · {anio}",
                "nota",
                puntos,
                maximo=7,
                tipo="dispersion",
                ayuda="Eje horizontal: cantidad de notas. Eje vertical: promedio. Cada punto abre una ficha; más notas no implica mejor rendimiento.",
            )
        )
    if previo:
        year, semester = previo
        cambios = []
        for alumno in alumnos:
            antes = valores.get((alumno.pk, year, semester))
            ahora = valores.get((alumno.pk, anio, semestre))
            if antes and ahora:
                p = punto(
                    f"{alumno.nombre} {alumno.apellido}",
                    ahora["promedio"] - antes["promedio"],
                    enlace_ficha(curso, alumno, semestre, anio, parametros),
                    tono,
                )
                p.update(
                    before=antes["promedio"],
                    after=ahora["promedio"],
                    detail=f'S{semester} {year}: {antes["promedio"]:.2f} ({antes["cantidad"]} notas) → S{semestre} {anio}: {ahora["promedio"]:.2f} ({ahora["cantidad"]} notas)',
                )
                cambios.append(p)
        charts.append(
            grafico(
                "cambio-promedios",
                "Cambio respecto al semestre anterior con notas",
                f"S{semester} · {year} → S{semestre} · {anio}",
                "puntos",
                cambios,
                maximo=6,
                tipo="cambios",
                ayuda="Diferencia de promedios, de −6 a +6. Solo estudiantes con notas en ambos períodos. Selecciona un estudiante para revisar su comparación y calificaciones.",
            )
        )
    elif not ficha:
        charts.append(
            grafico(
                "cambio-promedios",
                "Cambio entre semestres",
                f"Semestre {semestre} · {anio}",
                "puntos",
                [],
                tipo="cambios",
                ayuda="La comparación aparecerá cuando haya notas de al menos dos períodos. No se inventan resultados anteriores.",
            )
        )
    return charts
