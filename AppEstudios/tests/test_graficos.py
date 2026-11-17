"""Gráficos con significado, períodos correctos y destinos autorizados."""

from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from django.urls import reverse
from django.utils import timezone
from ..models import Inscripcion, RegistroEstudio
from .base import PortalTestCase


class GraficosTests(PortalTestCase):
    def test_exploration_history_is_limited_and_queries_are_batched(self):
        from ..consultas.exploracion import historia_exploracion

        for year in range(2015, 2027):
            self.nota(self.a, 5, semestre=1, anio=year)
            self.nota(self.a, 6, semestre=2, anio=year)
        self.nota(self.a, 7, anio=2027)
        with self.assertNumQueries(2):
            history = historia_exploracion(self.a, [self.est, self.est2], 2, 2026)
        self.assertEqual(len(history["periodos"]), 8)
        self.assertEqual(history["periodos"][-1], (2026, 2))
        self.assertEqual(history["previo"], (2026, 1))
        self.assertEqual(len(history["valores"]), 8)

    def test_exploration_scopes_history_and_distinguishes_missing_grades(self):
        Inscripcion.objects.create(estudiante=self.est2, sala=self.a)
        self.nota(self.a, 3, semestre=1)
        self.nota(self.a, 5)
        self.nota(self.a, 7)
        self.nota(self.b, 1)
        self.nota(self.a, 1, anio=2027)
        self.login(self.prof)
        response = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2026}
        )
        charts = {c["id"]: c for c in response.context["charts"]}
        matrix = charts["historia-estudiantes"]
        self.assertEqual(matrix["columns"], ["S1 · 2026", "S2 · 2026"])
        self.assertEqual([p["value"] for p in matrix["points"]], [3, 6, 0, 0])
        self.assertEqual(
            [p["missing"] for p in matrix["points"]], [False, False, True, True]
        )
        scatter = charts["promedio-cantidad"]["points"]
        self.assertEqual([(p["x"], p["value"]) for p in scatter], [(2, 6)])
        changes = charts["cambio-promedios"]["points"]
        self.assertEqual(
            [(p["before"], p["after"], p["value"]) for p in changes], [(3, 6, 3)]
        )
        missing = self.client.get(matrix["points"][-1]["url"])
        self.assertEqual(missing.status_code, 200)
        self.assertIsNone(missing.context["promedio"])

    def test_filtered_chart_links_return_to_same_range_and_page(self):
        self.nota(self.a, 3, semestre=1)
        self.nota(self.a, 5)
        self.login(self.prof)
        query = {"semestre": 2, "anio": 2026, "banda": 4, "pagina_estudiantes": 1}
        response = self.client.get(self.url(self.a, "calificaciones"), query)
        charts = {c["id"]: c for c in response.context["charts"]}
        for chart_id in (
            "estudiantes",
            "historia-estudiantes",
            "promedio-cantidad",
            "cambio-promedios",
        ):
            ficha = self.client.get(charts[chart_id]["points"][-1]["url"])
            self.assertEqual(ficha.status_code, 200)
            back = ficha.context["url_volver"]
            self.assertEqual(
                parse_qs(urlsplit(back).query), {k: [str(v)] for k, v in query.items()}
            )
            history = next(
                c for c in ficha.context["charts"] if c["id"] == "historia-curso"
            )
            previous = self.client.get(history["points"][0]["url"])
            self.assertEqual(previous.context["url_volver"], back)

    def test_comparison_excludes_students_without_both_periods(self):
        Inscripcion.objects.create(estudiante=self.est2, sala=self.a)
        self.nota(self.a, 6, semestre=1)
        self.nota(self.a, 4)
        self.nota(self.a, 7, estudiante=self.est2)
        self.login(self.prof)
        response = self.client.get(self.url(self.a, "calificaciones"))
        changes = next(
            c for c in response.context["charts"] if c["id"] == "cambio-promedios"
        )
        self.assertEqual([p["value"] for p in changes["points"]], [-2])
        self.login()
        response = self.client.get(self.url(self.a, "calificaciones"))
        self.assertFalse(
            {"historia-estudiantes", "promedio-cantidad", "cambio-promedios"}
            & {c["id"] for c in response.context["charts"]}
        )

    def test_return_link_cannot_redirect_outside_course(self):
        self.login(self.prof)
        response = self.client.get(
            reverse("ficha_estudiante", args=[self.a.pk, self.est.pk]),
            {"volver": "next=https://example.com&semestre=1&anio=2026&curso=999"},
        )
        back = urlsplit(response.context["url_volver"])
        self.assertFalse(back.netloc)
        self.assertEqual(back.path, self.url(self.a, "calificaciones"))
        self.assertEqual(parse_qs(back.query), {"semestre": ["1"], "anio": ["2026"]})

    def test_histograma_cuenta_promedios_en_seis_intervalos_iguales(self):
        Inscripcion.objects.create(estudiante=self.est2, sala=self.a)
        self.nota(self.a, 1)
        self.nota(self.a, 7)  # Promedio del estudiante: 4, no dos personas.
        self.nota(self.a, 7, estudiante=self.est2)
        self.nota(self.a, 1, anio=2025)
        self.login(self.prof)
        respuesta = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2026}
        )
        histograma = respuesta.context["charts"][0]
        self.assertEqual(histograma["type"], "histograma")
        self.assertEqual([p["value"] for p in histograma["points"]], [0, 0, 0, 1, 0, 1])
        respuesta = self.client.get(histograma["points"][3]["url"])
        self.assertEqual(
            {n.estudiante_id for n in respuesta.context["notas"]}, {self.est.pk}
        )
        self.assertEqual(len(respuesta.context["notas"]), 2)
        self.assertEqual(
            respuesta.context["total_notas"], 3
        )  # Indicador del curso completo.

    def test_notas_individuales_son_puntos_sin_falsa_linea_temporal(self):
        self.nota(self.a, 3)
        self.nota(self.a, 5)
        self.login()
        respuesta = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2026}
        )
        grafico = respuesta.context["charts"][0]
        self.assertEqual(grafico["type"], "puntos")
        self.assertEqual(grafico["orientacion"], "vertical")
        self.assertIn("no representa fechas", grafico["help"])
        self.assertEqual(respuesta.context["nota_minima"], 3)
        self.assertEqual(respuesta.context["nota_maxima"], 5)

    def test_una_nota_se_muestra_como_referencia_compacta(self):
        self.nota(self.a, 5)
        self.login()
        respuesta = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2026}
        )
        self.assertEqual(respuesta.context["charts"][0]["orientacion"], "horizontal")

    def test_historia_de_ficha_no_sale_del_estudiante(self):
        self.nota(self.a, 3, semestre=1)
        self.nota(self.a, 5)
        self.nota(self.a, 7, estudiante=self.est2)
        self.login(self.prof)
        url = reverse("ficha_estudiante", args=[self.a.pk, self.est.pk])
        respuesta = self.client.get(url, {"semestre": 2, "anio": 2026})
        historia = next(
            c for c in respuesta.context["charts"] if c["id"] == "historia-curso"
        )
        self.assertEqual([p["value"] for p in historia["points"]], [3, 5])
        for punto in historia["points"]:
            self.assertTrue(punto["url"].startswith(url))

    def test_perfil_del_curso_filtra_solo_sus_estudiantes(self):
        self.login(self.prof)
        respuesta = self.client.get(self.url(self.a, "resumen"))
        charts = {c["id"]: c for c in respuesta.context["charts"]}
        self.assertEqual(charts["edades"]["type"], "columnas")
        self.assertEqual(charts["edades"]["points"][0]["value"], 1)
        filtrada = self.client.get(charts["edades"]["points"][0]["url"])
        self.assertEqual(list(filtrada.context["alumnos"]), [self.est])
        filtrada = self.client.get(charts["viajes"]["points"][0]["url"])
        self.assertEqual(list(filtrada.context["alumnos"]), [self.est])
        self.assertEqual(
            self.client.get(self.url(self.c, "estudiantes"), {"edad": 21}).status_code,
            404,
        )

    def test_anillo_representa_minutos_no_promedios(self):
        hoy = timezone.localdate()
        for sala, minutos in [(self.a, 30), (self.b, 60), (None, 10)]:
            RegistroEstudio.objects.create(
                estudiante=self.est, sala=sala, fecha=hoy, minutos=minutos
            )
        self.login()
        respuesta = self.client.get(reverse("estudio"))
        anillo = next(
            c for c in respuesta.context["charts"] if c["id"] == "estudio-cursos"
        )
        self.assertEqual(anillo["type"], "anillo")
        self.assertEqual(anillo["unit"], "minutos")
        self.assertEqual(sum(p["value"] for p in anillo["points"]), 100)
        self.assertEqual(
            [p["url"] for p in anillo["points"]],
            [self.url(self.a, "calificaciones"), self.url(self.b, "calificaciones"), reverse("rendimiento")],
        )
        for punto in anillo["points"]:
            self.assertEqual(self.client.get(punto["url"]).status_code, 200)

    def test_mapa_de_calor_no_mezcla_usuarios_ni_inventa_dias_futuros(self):
        hoy = timezone.localdate()
        RegistroEstudio.objects.create(estudiante=self.est, fecha=hoy, minutos=25)
        RegistroEstudio.objects.create(
            estudiante=self.est, fecha=hoy - timedelta(days=40), minutos=999
        )
        RegistroEstudio.objects.create(estudiante=self.est2, fecha=hoy, minutos=888)
        self.login()
        respuesta = self.client.get(reverse("estudio"))
        calor = next(c for c in respuesta.context["charts"] if c["id"] == "constancia")
        self.assertEqual(calor["type"], "calor")
        self.assertEqual(sum(p["value"] for p in calor["points"]), 25)
        self.assertLessEqual(len(calor["points"]), 28)
        self.assertEqual(calor["points"][-1]["label"], hoy.strftime("%d/%m/%Y"))
        self.assertEqual(respuesta.context["minutos_semana"], 25)
        filtrada = self.client.get(reverse("estudio") + calor["points"][-1]["url"])
        self.assertEqual([r.minutos for r in filtrada.context["historial"]], [25])
