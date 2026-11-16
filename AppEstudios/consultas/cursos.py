"""Consultas acotadas por curso, usuario y período; sin decisiones de presentación."""

from datetime import timedelta

from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import Http404

from ..paginacion import navegacion, paginar

RANGOS = [
    (1, 4, "1,0 a <4,0"),
    (4, 5, "4,0 a <5,0"),
    (5, 6, "5,0 a <6,0"),
    (6, 7.01, "6,0 a 7,0"),
]


def notas_del_curso(curso, semestre, anio, estudiante=None, ficha=None):
    notas = curso.calificaciones.filter(semestre=semestre, anio=anio)
    if estudiante is not None:
        notas = notas.filter(estudiante=estudiante)
    if ficha is not None:
        notas = notas.filter(estudiante=ficha)
    return notas


def entregas_del_curso(curso, profesor, estudiante=None):
    tareas = curso.tareas.all()
    if not profesor:
        tareas = tareas.filter(Q(estudiante=estudiante) | Q(estudiante__isnull=True))
    else:
        # Las copias antiguas por alumno se agrupan en SQL antes de paginar.
        ids = (
            tareas.order_by()
            .values("titulo", "fecha_entrega", "materia_id")
            .annotate(primero=Min("pk"))
            .values("primero")
        )
        tareas = tareas.filter(pk__in=ids)
    return tareas.select_related("estudiante", "materia").order_by(
        "fecha_entrega", "titulo", "pk"
    )


def datos_curso(
    curso, seccion, profesor, estudiante, ficha, semestre, anio, parametros
):
    datos = {
        "notas": [],
        "promedio": None,
        "entregas": [],
        "alumnos": [],
        "total_alumnos": 0,
        "total_entregas": 0,
        "distribucion": [],
        "histograma": [],
        "banda_seleccionada": None,
        "alumnos_grafico": [],
        "promedios": {},
        "rango_label": None,
        "habitos": [],
        "evolucion": [],
        "periodos": [],
        "total_notas": 0,
        "estudiantes_con_notas": 0,
        "nota_minima": None,
        "nota_maxima": None,
        "edades": [],
        "viajes": [],
    }
    notas = notas_del_curso(curso, semestre, anio, estudiante, ficha)
    alumnos = curso.alumnos_inscritos.order_by("apellido", "nombre", "pk")
    if seccion == "resumen":
        datos["promedio"] = notas.aggregate(valor=Avg("nota"))["valor"]
        datos["total_entregas"] = entregas_del_curso(
            curso, profesor, estudiante
        ).count()
        datos["total_alumnos"] = alumnos.count() if profesor else 0
        if profesor:
            datos["edades"] = list(
                alumnos.values("edad").annotate(total=Count("pk")).order_by("edad")
            )
            datos["viajes"] = list(
                alumnos.values("tiempo_viaje")
                .annotate(total=Count("pk"))
                .order_by("tiempo_viaje")
            )
        historia = curso.calificaciones.all()
        if estudiante:
            historia = historia.filter(estudiante=estudiante)
        datos["evolucion"] = list(
            historia.values("anio", "semestre")
            .annotate(promedio=Avg("nota"))
            .order_by("anio", "semestre")
        )
    elif seccion == "calificaciones" or (
        seccion == "estudiantes" and ficha is not None
    ):
        # Resúmenes sobre todo el período, sin cargar cada nota ni depender de la página.
        agregados = list(
            notas.values("estudiante_id").annotate(
                promedio=Avg("nota"),
                total=Sum("nota"),
                cantidad=Count("pk"),
                minima=Min("nota"),
                maxima=Max("nota"),
            )
        )
        cantidad = sum(fila["cantidad"] for fila in agregados)
        datos["total_notas"] = cantidad
        datos["estudiantes_con_notas"] = len(agregados)
        datos["nota_minima"] = min((f["minima"] for f in agregados), default=None)
        datos["nota_maxima"] = max((f["maxima"] for f in agregados), default=None)
        datos["promedio"] = (
            sum(fila["total"] for fila in agregados) / cantidad if cantidad else None
        )
        promedios = {fila["estudiante_id"]: fila["promedio"] for fila in agregados}
        datos["promedios"] = promedios
        if profesor and seccion == "calificaciones":
            inscritos = list(alumnos)
            datos["alumnos"] = inscritos
            datos["total_alumnos"] = len(inscritos)
            distribucion = [
                {
                    "label": label,
                    "alumnos": [
                        a
                        for a in inscritos
                        if a.pk in promedios and minimo <= promedios[a.pk] < maximo
                    ],
                }
                for minimo, maximo, label in RANGOS
            ]
            datos["distribucion"] = distribucion
            bandas = [
                {
                    "label": f"{inicio},0–<{inicio+1},0" if inicio < 6 else "6,0–7,0",
                    "alumnos": [
                        a
                        for a in inscritos
                        if a.pk in promedios
                        and inicio
                        <= promedios[a.pk]
                        < (inicio + 1 if inicio < 6 else 7.01)
                    ],
                }
                for inicio in range(1, 7)
            ]
            datos["histograma"] = bandas
            rango = parametros.get("rango", "")
            if rango in ("0", "1", "2", "3"):
                elegidos = distribucion[int(rango)]
                datos["rango_label"] = elegidos["label"]
                inscritos = elegidos["alumnos"]
                notas = notas.filter(estudiante_id__in=[a.pk for a in inscritos])
            banda = parametros.get("banda", "")
            if banda in tuple(str(i) for i in range(6)):
                datos["banda_seleccionada"] = int(banda)
                elegidos = bandas[int(banda)]
                datos["rango_label"] = elegidos["label"]
                inscritos = elegidos["alumnos"]
                notas = notas.filter(estudiante_id__in=[a.pk for a in inscritos])
            con_notas = [a for a in inscritos if a.pk in promedios]
            pagina_alumnos = paginar(con_notas, parametros, "pagina_estudiantes")
            datos["alumnos_grafico"] = list(pagina_alumnos)
            datos["paginacion_alumnos"] = navegacion(
                pagina_alumnos, parametros, "pagina_estudiantes", "estudiantes-grafico"
            )
        pagina = paginar(
            notas.select_related("estudiante", "materia").order_by("pk"), parametros
        )
        datos["notas"] = pagina
        datos["inicio_notas"] = pagina.start_index() - 1
        datos["paginacion_notas"] = navegacion(pagina, parametros, ancla="tabla-notas")
        if cantidad:
            historia = curso.calificaciones.all()
            if estudiante is not None:
                historia = historia.filter(estudiante=estudiante)
            if ficha is not None:
                historia = historia.filter(estudiante=ficha)
            datos["evolucion"] = list(
                historia.values("anio", "semestre")
                .annotate(promedio=Avg("nota"))
                .order_by("anio", "semestre")
            )
    elif seccion == "estudiantes":
        if parametros.get("edad", "").isdecimal():
            edad = int(parametros["edad"])
            alumnos = alumnos.filter(edad=edad)
            datos["filtro_estudiantes"] = f"Edad: {edad} años"
        viaje = parametros.get("viaje", "")
        if viaje:
            from ..models import Estudiante

            if viaje in dict(Estudiante.TIEMPO_VIAJE_CHOICES):
                alumnos = alumnos.filter(tiempo_viaje=viaje)
                datos["filtro_estudiantes"] = (
                    "Tiempo de viaje: " + dict(Estudiante.TIEMPO_VIAJE_CHOICES)[viaje]
                )
            else:
                raise Http404("Filtro no disponible.")
        pagina = paginar(alumnos, parametros)
        datos["alumnos"] = pagina
        datos["paginacion_alumnos"] = navegacion(
            pagina, parametros, ancla="lista-estudiantes"
        )
    elif seccion == "tareas":
        tareas = entregas_del_curso(curso, profesor, estudiante)
        entrega = parametros.get("entrega", "")
        if entrega:
            if not entrega.isdecimal():
                raise Http404("Entrega no disponible.")
            seleccionada = get_object_or_404(tareas, pk=entrega)
            tareas = tareas.filter(pk=seleccionada.pk)
            datos["entrega_seleccionada"] = seleccionada
        pagina = paginar(tareas, parametros)
        datos["entregas"] = pagina
        datos["paginacion_entregas"] = navegacion(
            pagina, parametros, ancla="tabla-tareas"
        )
    elif seccion == "habitos":
        hoy = timezone.localdate()
        lunes = hoy - timedelta(days=hoy.weekday())
        pagina = paginar(alumnos, parametros)
        visibles = list(pagina)
        minutos = dict(
            curso.registros_estudio.filter(
                estudiante__in=visibles, fecha__range=(lunes, hoy)
            )
            .values("estudiante_id")
            .annotate(total=Sum("minutos"))
            .values_list("estudiante_id", "total")
        )
        datos.update(
            {
                "hoy": hoy,
                "lunes": lunes,
                "habitos": [
                    {"alumno": a, "minutos": minutos.get(a.pk)} for a in visibles
                ],
                "paginacion_habitos": navegacion(
                    pagina, parametros, ancla="tabla-habitos"
                ),
            }
        )
    elif seccion == "configuracion":
        periodos = set(curso.calificaciones.values_list("semestre", "anio").distinct())
        periodos.add((curso.semestre_actual, curso.anio_actual))
        datos["periodos"] = sorted(periodos, key=lambda p: (p[1], p[0]), reverse=True)
    return datos
