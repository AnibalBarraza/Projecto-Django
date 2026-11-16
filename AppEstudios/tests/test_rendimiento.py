"""Pruebas de rendimiento en el flujo autenticado por curso."""

from django.urls import reverse
from ..models import Sala, Inscripcion


from .base import PortalTestCase


class RendimientoTests(PortalTestCase):
    def test_equal_weight_course_average_and_year_filter(self):
        self.nota(self.a, 7)
        self.nota(self.b, 1)
        self.nota(self.b, 3)
        self.nota(self.b, 7, anio=2025)
        self.login()
        response = self.client.get(
            reverse("rendimiento"), {"semestre": 2, "anio": 2026}
        )
        self.assertEqual(response.context["promedio_general"], 4.5)
        self.assertContains(response, "4,50")
        empty = Sala.objects.create(
            profesor=self.prof, asignatura="Química", nombre_profesor="Docente"
        )
        Inscripcion.objects.create(estudiante=self.est, sala=empty)
        response = self.client.get(
            reverse("rendimiento"), {"semestre": 2, "anio": 2026}
        )
        self.assertEqual(response.context["promedio_general"], 4.5)
        self.assertContains(response, "Sin calificaciones")

    def test_no_data_is_not_zero(self):
        self.login()
        for url in [reverse("rendimiento"), self.url()]:
            self.assertContains(self.client.get(url), "Sin calificaciones")

    def test_chart_drilldown_keeps_period_and_filters_students(self):
        self.nota(self.a, 3)
        Inscripcion.objects.create(estudiante=self.est2, sala=self.a)
        self.nota(self.a, 6, estudiante=self.est2)
        self.login(self.prof)
        response = self.client.get(
            self.url(self.a, "calificaciones"),
            {"semestre": 2, "anio": 2026, "rango": "0"},
        )
        charts = {c["id"]: c for c in response.context["charts"]}
        distribution = charts["distribucion"]["points"]
        self.assertEqual([p["value"] for p in distribution], [0, 0, 1, 0, 0, 1])
        self.assertIn("semestre=2&anio=2026&banda=0", distribution[0]["url"])
        student_chart = charts["estudiantes"]["points"]
        self.assertEqual(len(student_chart), 1)
        self.assertIn(
            reverse("ficha_estudiante", args=[self.a.pk, self.est.pk]),
            student_chart[0]["url"],
        )
        self.assertEqual(
            {n.estudiante_id for n in response.context["notas"]}, {self.est.pk}
        )
        response = self.client.get(student_chart[0]["url"])
        self.assertEqual(response.context["charts"][0]["points"][0]["value"], 3)
        self.assertEqual(
            response.context["charts"][0]["points"][0]["url"],
            "#detalle-" + str(self.a.calificaciones.get(estudiante=self.est).pk),
        )

    def test_chart_payload_escapes_html_and_excludes_other_users(self):
        self.a.asignatura = "<script>alert(1)</script>"
        self.a.save()
        self.nota(self.a, 5)
        self.nota(self.c, 1, estudiante=self.est2)
        self.login()
        response = self.client.get(
            reverse("rendimiento"), {"semestre": 2, "anio": 2026}
        )
        self.assertEqual(len(response.context["charts"][0]["points"]), 1)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "Ver datos y enlaces del gráfico")
