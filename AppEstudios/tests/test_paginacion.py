"""Páginas acotadas sin perder filtros, datos globales ni destinos de gráficos."""

from datetime import date
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from ..models import Calificacion, Estudiante, Inscripcion, Tarea
from .base import PortalTestCase


class PaginacionTests(PortalTestCase):
    def crear_notas(self):
        return Calificacion.objects.bulk_create(
            [
                Calificacion(
                    sala=self.a,
                    estudiante=self.est,
                    materia=self.m,
                    nota=1 if i < 30 else 7,
                    semestre=2,
                    anio=2026,
                )
                for i in range(33)
            ]
        )

    def test_notas_y_grafico_paginan_sin_cambiar_promedio(self):
        notas = self.crear_notas()
        self.login()
        url = self.url(self.a, "calificaciones")
        respuesta = self.client.get(url, {"semestre": 2, "anio": 2026})
        self.assertEqual(len(respuesta.context["notas"]), 30)
        self.assertEqual(len(respuesta.context["charts"][0]["points"]), 30)
        self.assertAlmostEqual(respuesta.context["promedio"], 51 / 33)
        siguiente = respuesta.context["paginacion_notas"]["siguiente"]
        self.assertIn("semestre=2", siguiente)
        self.assertIn("anio=2026", siguiente)
        segunda = self.client.get(url + siguiente)
        self.assertEqual(list(segunda.context["notas"]), notas[30:])
        self.assertEqual(segunda.context["charts"][0]["points"][0]["label"], "Nota 31")
        self.assertEqual(
            segunda.context["charts"][0]["points"][0]["url"],
            "#detalle-" + str(notas[30].pk),
        )
        self.assertAlmostEqual(segunda.context["promedio"], 51 / 33)

    def test_resumen_y_rendimiento_usan_todo_el_periodo(self):
        self.crear_notas()
        self.login()
        resumen = self.client.get(self.url(), {"semestre": 2, "anio": 2026})
        general = self.client.get(reverse("rendimiento"), {"semestre": 2, "anio": 2026})
        self.assertAlmostEqual(resumen.context["promedio"], 51 / 33)
        self.assertAlmostEqual(general.context["promedio_general"], 51 / 33)
        self.assertEqual(resumen.context["notas"], [])

    def test_rango_se_conserva_al_paginar_notas(self):
        self.crear_notas()
        self.login(self.prof)
        url = self.url(self.a, "calificaciones")
        respuesta = self.client.get(
            url, {"semestre": 2, "anio": 2026, "rango": "0", "pagina": "2"}
        )
        self.assertEqual(len(respuesta.context["notas"]), 3)
        self.assertEqual(respuesta.context["distribucion"][0]["alumnos"], [self.est])
        self.assertIn("rango=0", respuesta.context["paginacion_notas"]["anterior"])
        self.assertEqual(respuesta.context["charts"][1]["points"][0]["value"], 51 / 33)

    def test_pagina_invalida_no_expone_otros_cursos(self):
        self.crear_notas()
        otra = self.nota(self.c, 7, estudiante=self.est2)
        self.login()
        for pagina in ["texto", "-1", "999999"]:
            respuesta = self.client.get(
                self.url(self.a, "calificaciones"),
                {"semestre": 2, "anio": 2026, "pagina": pagina},
            )
            self.assertEqual(respuesta.status_code, 200)
            self.assertLessEqual(len(respuesta.context["notas"]), 30)
            self.assertNotIn(otra.pk, [n.pk for n in respuesta.context["notas"]])

    def test_tareas_agrupa_copias_antes_de_paginar(self):
        tareas = []
        for i in range(33):
            for estudiante in [self.est, self.est2]:
                tareas.append(
                    Tarea(
                        sala=self.a,
                        estudiante=estudiante,
                        materia=self.m,
                        titulo=f"Entrega {i:02}",
                        fecha_entrega=date(2026, 11, 18),
                    )
                )
        Tarea.objects.bulk_create(tareas)
        self.login(self.prof)
        respuesta = self.client.get(self.url(self.a, "tareas"))
        self.assertEqual(respuesta.context["entregas"].paginator.count, 33)
        self.assertEqual(len(respuesta.context["entregas"]), 30)
        segunda = self.client.get(self.url(self.a, "tareas"), {"pagina": 2})
        self.assertEqual(len(segunda.context["entregas"]), 3)
        self.assertEqual(segunda.context["entregas"][0].titulo, "Entrega 30")

    def test_calendario_abre_entrega_fuera_de_primera_pagina(self):
        tareas = Tarea.objects.bulk_create(
            [
                Tarea(
                    sala=self.a,
                    materia=self.m,
                    titulo=f"Tarea {i:02}",
                    fecha_entrega=date(2026, 11, 18),
                )
                for i in range(33)
            ]
        )
        self.login()
        respuesta = self.client.get(
            self.url(self.a, "tareas"), {"entrega": tareas[-1].pk}
        )
        self.assertEqual(list(respuesta.context["entregas"]), [tareas[-1]])
        calendario = self.client.get(reverse("calendario"), {"mes": 11, "anio": 2026})
        self.assertContains(
            calendario, f"?entrega={tareas[-1].pk}#tarea-{tareas[-1].pk}"
        )
        ajena = Tarea.objects.create(
            sala=self.c,
            estudiante=self.est2,
            materia=self.m,
            titulo="Privada",
            fecha_entrega=date(2026, 11, 18),
        )
        self.assertEqual(
            self.client.get(
                self.url(self.a, "tareas"), {"entrega": ajena.pk}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                self.url(self.a, "tareas"), {"entrega": "invalida"}
            ).status_code,
            404,
        )

    def crear_estudiantes(self):
        estudiantes = Estudiante.objects.bulk_create(
            [
                Estudiante(
                    nombre=f"Alumno {i:02}",
                    apellido="Pérez",
                    edad=20,
                    tiempo_viaje="< 15 min",
                )
                for i in range(34)
            ]
        )
        Inscripcion.objects.bulk_create(
            [Inscripcion(sala=self.a, estudiante=e) for e in estudiantes]
        )
        return estudiantes

    def test_listado_estudiantes_y_habitos_acotados(self):
        self.crear_estudiantes()
        self.login(self.prof)
        listado = self.client.get(self.url(self.a, "estudiantes"))
        self.assertEqual(len(listado.context["alumnos"]), 30)
        segunda = self.client.get(self.url(self.a, "estudiantes"), {"pagina": 2})
        self.assertEqual(len(segunda.context["alumnos"]), 5)
        habitos = self.client.get(self.url(self.a, "habitos"))
        self.assertEqual(len(habitos.context["habitos"]), 30)
        segunda = self.client.get(self.url(self.a, "habitos"), {"pagina": 2})
        self.assertEqual(len(segunda.context["habitos"]), 5)

    def test_grafico_estudiantes_paginado_distribucion_completa(self):
        estudiantes = self.crear_estudiantes()
        Calificacion.objects.bulk_create(
            [
                Calificacion(
                    sala=self.a,
                    estudiante=e,
                    materia=self.m,
                    nota=5,
                    semestre=2,
                    anio=2026,
                )
                for e in estudiantes
            ]
        )
        self.login(self.prof)
        respuesta = self.client.get(
            self.url(self.a, "calificaciones"),
            {"semestre": 2, "anio": 2026, "rango": "2", "pagina_estudiantes": "2"},
        )
        self.assertEqual(len(respuesta.context["charts"][1]["points"]), 4)
        self.assertEqual(respuesta.context["charts"][0]["points"][4]["value"], 34)
        anterior = respuesta.context["paginacion_alumnos"]["anterior"]
        self.assertIn("rango=2", anterior)
        self.assertIn("semestre=2", anterior)

    def test_consultas_acotadas_con_datos_en_pagina(self):
        Tarea.objects.bulk_create(
            [
                Tarea(
                    sala=self.a,
                    materia=self.m,
                    titulo=f"Entrega {i}",
                    fecha_entrega=date(2026, 11, 18),
                )
                for i in range(60)
            ]
        )
        self.crear_estudiantes()
        self.login(self.prof)
        for seccion, maximo in [("tareas", 6), ("habitos", 7)]:
            with CaptureQueriesContext(connection) as capturadas:
                respuesta = self.client.get(self.url(self.a, seccion))
            self.assertEqual(respuesta.status_code, 200)
            self.assertLessEqual(len(capturadas), maximo)

    def test_selector_de_notas_no_consulta_una_sala_por_estudiante(self):
        self.login(self.prof)

        def contar():
            with CaptureQueriesContext(connection) as consultas:
                respuesta = self.client.get(self.url(self.a, "calificaciones"))
            return len(consultas), respuesta

        antes, _ = contar()
        estudiantes = self.crear_estudiantes()
        Estudiante.objects.filter(pk__in=[e.pk for e in estudiantes]).update(
            sala=self.a
        )
        despues, respuesta = contar()
        self.assertLessEqual(despues, antes + 1)
        self.assertContains(respuesta, "Alumno 00 Pérez")
