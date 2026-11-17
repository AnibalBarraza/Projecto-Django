from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from AppEstudios.models import Calificacion, Estudiante, RegistroEstudio, Sala, Tarea


class DemoTests(TestCase):
    def test_demo_accounts_pages_and_repeated_run(self):
        existing = get_user_model().objects.create_user("existente", password="Original123")
        call_command("crear_demo", stdout=StringIO())
        self.assertEqual(Sala.objects.count(), 4)
        self.assertEqual(Estudiante.objects.count(), 16)
        self.assertEqual(Tarea.objects.count(), 16)
        self.assertEqual(Calificacion.objects.values("anio", "semestre").distinct().count(), 3)
        self.assertTrue(RegistroEstudio.objects.filter(sala__isnull=True).exists())
        for username in ["demo_profe_1", "demo_estudiante_01"]:
            self.client.force_login(get_user_model().objects.get(username=username))
            for url in [reverse("tablero"), reverse("rendimiento")]:
                self.assertEqual(self.client.get(url).status_code, 200)
            curso = Sala.objects.order_by("pk").first()
            self.assertEqual(self.client.get(reverse("curso_seccion", args=[curso.pk, "calificaciones"])).status_code, 200)
        with self.assertRaises(CommandError):
            call_command("crear_demo", stdout=StringIO())
        self.assertEqual(get_user_model().objects.count(), 19)
        existing.refresh_from_db()
        self.assertTrue(existing.check_password("Original123"))
