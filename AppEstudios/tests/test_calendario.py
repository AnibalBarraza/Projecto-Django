"""Pruebas de calendario en el flujo autenticado por curso."""

from datetime import date
from django.urls import reverse
from ..models import Tarea


from .base import PortalTestCase


class CalendarioTests(PortalTestCase):
    def test_calendar_deduplicates_teacher_legacy_tasks_and_scopes_students(self):
        for est in [self.est, self.est2]:
            Tarea.objects.create(
                sala=self.a,
                estudiante=est,
                materia=self.m,
                titulo="Entrega común",
                fecha_entrega=date(2026, 11, 18),
            )
        Tarea.objects.create(
            sala=self.b,
            estudiante=self.est2,
            materia=self.m,
            titulo="Tarea privada",
            fecha_entrega=date(2026, 11, 20),
        )
        self.login(self.prof)
        response = self.client.get(
            reverse("calendario"), {"mes": 11, "anio": 2026, "curso": self.a.pk}
        )
        self.assertEqual(len(response.context["agenda"][0]["eventos"]), 1)
        self.assertEqual(
            self.client.get(reverse("calendario"), {"curso": self.c.pk}).status_code,
            404,
        )
        self.login()
        response = self.client.get(reverse("calendario"), {"mes": 11, "anio": 2026})
        self.assertContains(response, "Entrega común")
        self.assertNotContains(response, "Tarea privada")
        self.assertContains(response, "Mes siguiente")
        self.assertContains(response, "agenda")

    def test_calendar_only_in_calendar_page(self):
        self.login()
        for url in [
            self.url(),
            self.url(self.a, "calificaciones"),
            reverse("estudio"),
            reverse("rendimiento"),
        ]:
            response = self.client.get(url)
            self.assertNotContains(response, "Calendario mensual")
        self.assertContains(
            self.client.get(reverse("calendario")), "Calendario mensual"
        )
