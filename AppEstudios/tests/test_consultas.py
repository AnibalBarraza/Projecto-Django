"""Pruebas de consultas en el flujo autenticado por curso."""

from django.urls import reverse
from django.db import connection


from .base import PortalTestCase


class ConsultasTests(PortalTestCase):
    def test_query_budgets_for_independent_pages(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        self.login(self.prof)
        for section, maximum in [("tareas", 6), ("configuracion", 5), ("habitos", 7)]:
            with CaptureQueriesContext(connection) as captured:
                response = self.client.get(self.url(self.a, section))
            self.assertEqual(response.status_code, 200)
            self.assertLessEqual(len(captured), maximum, section)
            sql = " ".join(q["sql"].lower() for q in captured)
            if section in ("tareas", "habitos"):
                self.assertNotIn("appestudios_calificacion", sql)
            if section == "configuracion":
                self.assertNotIn("appestudios_tarea", sql)
                self.assertNotIn("appestudios_registroestudio", sql)

    def test_history_query_count_does_not_grow_with_periods(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        self.login(self.prof)

        def count():
            with CaptureQueriesContext(connection) as captured:
                self.client.get(reverse("rendimiento"))
            return len(captured)

        initial = count()
        for year in range(2010, 2027):
            for semester in (1, 2):
                self.nota(self.a, 5, semestre=semester, anio=year)
        self.assertEqual(count(), initial)
        self.assertLessEqual(initial, 5)
