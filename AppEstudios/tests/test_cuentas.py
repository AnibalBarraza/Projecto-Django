"""Pruebas de cuentas en el flujo autenticado por curso."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import Sala, Estudiante, Inscripcion


from .base import PortalTestCase


class CuentasTests(PortalTestCase):
    def test_anonymous_requires_login(self):
        for url in [
            reverse("tablero"),
            self.url(),
            reverse("calendario"),
            reverse("rendimiento"),
            reverse("estudio"),
        ]:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_registration_both_roles_and_no_admin_privileges(self):
        for rol in ["profesor", "estudiante"]:
            self.client.logout()
            response = self.client.post(
                reverse("registrarse"),
                {
                    "username": "nuevo_" + rol,
                    "first_name": "María",
                    "last_name": "Rojas",
                    "rol": rol,
                    "edad": 20,
                    "tiempo_viaje": "< 15 min",
                    "password1": "Segura-1234-nueva",
                    "password2": "Segura-1234-nueva",
                },
            )
            self.assertEqual(response.status_code, 302)
            user = get_user_model().objects.get(username="nuevo_" + rol)
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)
            self.assertEqual(
                user.groups.filter(name="Profesores").exists(), rol == "profesor"
            )
            self.assertEqual(
                Estudiante.objects.filter(usuario=user).exists(), rol == "estudiante"
            )

    def test_login_both_roles(self):
        for user in [self.user, self.prof]:
            self.client.logout()
            response = self.client.post(
                reverse("ingresar"), {"username": user.username, "password": "clave"}
            )
            self.assertRedirects(
                response, reverse("mi_cuenta"), fetch_redirect_response=False
            )
            self.assertRedirects(
                self.client.get(reverse("mi_cuenta")), reverse("tablero")
            )

    def test_pending_role_does_not_link_legacy_name(self):
        pending = get_user_model().objects.create_user("pendiente", first_name="Ana")
        self.login(pending)
        self.assertContains(self.client.get(reverse("mi_cuenta")), "Completa tu cuenta")
        self.client.post(
            reverse("elegir_rol"),
            {"rol": "estudiante", "edad": 20, "tiempo_viaje": "< 15 min"},
        )
        self.assertNotEqual(Estudiante.objects.get(usuario=pending).pk, self.est.pk)
        self.client.post(reverse("elegir_rol"), {"rol": "profesor"})
        self.assertFalse(pending.groups.exists())

    def test_enrollment_is_idempotent_and_archived_rejected(self):
        self.login()
        for _ in range(2):
            self.client.post(
                reverse("inscribirse"), {"codigo_sala": self.c.codigo.lower()}
            )
        self.assertEqual(
            Inscripcion.objects.filter(estudiante=self.est, sala=self.c).count(), 1
        )
        self.c.archivada = True
        self.c.save()
        Inscripcion.objects.filter(estudiante=self.est, sala=self.c).delete()
        self.client.post(reverse("inscribirse"), {"codigo_sala": self.c.codigo})
        self.assertFalse(self.est.cursos.filter(pk=self.c.pk).exists())

    def test_task_without_students_is_saved_and_visible_to_future_enrollment(self):
        self.login(self.prof)
        nuevo = Sala.objects.create(
            profesor=self.prof, nombre_profesor="Docente", asignatura="Física"
        )
        self.client.post(
            self.url(nuevo, "tareas"),
            {"crear_tarea": "", "titulo": "Guía nueva", "fecha_entrega": "2026-12-01"},
        )
        self.assertIsNone(nuevo.tareas.get().estudiante_id)
        Inscripcion.objects.create(estudiante=self.est, sala=nuevo)
        self.login()
        self.assertContains(self.client.get(self.url(nuevo, "tareas")), "Guía nueva")

    def test_csrf_protection(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        client.force_login(self.prof)
        self.assertEqual(
            client.post(
                self.url(self.a, "calificaciones"),
                {"crear_nota": "", "nota": 7, "estudiante": self.est.pk},
            ).status_code,
            403,
        )
