"""Pruebas de estudio en el flujo autenticado por curso."""

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from ..models import RegistroEstudio


from .base import PortalTestCase


class EstudioTests(PortalTestCase):
    def test_study_update_by_day_course_and_global_sum(self):
        self.login()
        hoy = timezone.localdate().isoformat()

        def guardar(sala, minutos):
            return self.client.post(
                reverse("estudio"),
                {
                    "fecha": hoy,
                    "minutos": minutos,
                    "meta_semanal_minutos": 300,
                    "sala": sala,
                },
            )

        guardar("", 20)
        guardar("", 30)
        guardar(self.a.pk, 40)
        guardar(self.a.pk, 50)
        guardar(self.b.pk, 60)
        self.assertEqual(RegistroEstudio.objects.count(), 3)
        response = self.client.get(reverse("estudio"))
        self.assertEqual(response.context["minutos_semana"], 140)
        self.assertEqual(response.context["progreso_meta"], 47)
        self.assertContains(response, "Estudio general")
        guardar(self.c.pk, 10)
        self.assertEqual(RegistroEstudio.objects.count(), 3)

    def test_study_validation_and_privacy(self):
        self.login()
        for fecha, minutos in [
            ("2200-01-01", 10),
            (timezone.localdate().isoformat(), 1441),
            (timezone.localdate().isoformat(), -1),
        ]:
            response = self.client.post(
                reverse("estudio"),
                {"fecha": fecha, "minutos": minutos, "meta_semanal_minutos": 300},
            )
            self.assertTrue(response.context["form"].errors)
        RegistroEstudio.objects.create(
            estudiante=self.est2, fecha=timezone.localdate(), minutos=987
        )
        self.assertNotContains(self.client.get(reverse("estudio")), "987")

    def test_habits_only_course_minutes_and_temporal_limit(self):
        for sala, minutos in [(None, 90), (self.a, 40), (self.b, 20)]:
            RegistroEstudio.objects.create(
                estudiante=self.est,
                sala=sala,
                fecha=timezone.localdate(),
                minutos=minutos,
            )
        self.login(self.prof)
        response = self.client.get(self.url(self.a, "habitos"))
        self.assertEqual(response.context["habitos"][0]["minutos"], 40)
        self.assertContains(response, "No se calcula una correlación")

    def test_unique_study_constraints(self):
        for sala in [None, self.a]:
            RegistroEstudio.objects.create(
                estudiante=self.est, sala=sala, fecha=timezone.localdate(), minutos=1
            )
            with self.assertRaises(IntegrityError), transaction.atomic():
                RegistroEstudio.objects.create(
                    estudiante=self.est,
                    sala=sala,
                    fecha=timezone.localdate(),
                    minutos=2,
                )

    def test_study_charts_filter_history_without_changing_weekly_total(self):
        today = timezone.localdate()
        for course, minutes in [(self.a, 30), (self.b, 60), (None, 20)]:
            RegistroEstudio.objects.create(
                estudiante=self.est, sala=course, fecha=today, minutos=minutes
            )
        self.login()
        response = self.client.get(reverse("estudio"), {"curso": self.a.pk})
        self.assertEqual(response.context["minutos_semana"], 110)
        self.assertEqual(
            [r.sala_id for r in response.context["historial"]], [self.a.pk]
        )
        chart = response.context["charts"][1]
        self.assertEqual(sum(p["value"] for p in chart["points"]), 110)
        self.assertEqual(
            self.client.get(reverse("estudio"), {"curso": self.c.pk}).status_code, 404
        )
        response = self.client.get(
            reverse("estudio"), {"fecha": today.isoformat(), "curso": "general"}
        )
        self.assertEqual([r.minutos for r in response.context["historial"]], [20])
