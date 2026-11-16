"""Inicio público y creación de cursos desde el tablero."""

from django.urls import reverse
from ..models import Sala
from .base import PortalTestCase


class InicioTests(PortalTestCase):
    def test_inicio_publico_independiente_del_tablero(self):
        with self.assertNumQueries(0):
            response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cada avance cuenta.")
        self.assertContains(response, reverse("ingresar"))
        self.assertContains(response, "Vista ilustrativa")
        self.assertNotContains(response, self.a.codigo)
        self.assertEqual(self.client.post(reverse("index")).status_code, 405)
        self.assertEqual(self.client.get(reverse("tablero")).status_code, 302)

    def test_inicio_autenticado_tiene_acceso_a_tablero(self):
        self.login()
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Ir a mi tablero")
        self.assertNotContains(response, self.a.codigo)

    def test_perfil_elegido_en_inicio_preselecciona_registro(self):
        for rol in ["profesor", "estudiante"]:
            response = self.client.get(reverse("registrarse"), {"rol": rol})
            self.assertEqual(response.context["form"].initial["rol"], rol)
        response = self.client.get(reverse("registrarse"), {"rol": "admin"})
        self.assertEqual(response.context["form"].initial["rol"], "estudiante")

    def test_crear_curso_tiene_enlace_arriba_y_alternativa_sin_javascript(self):
        self.login(self.prof)
        response = self.client.get(reverse("tablero"))
        html = response.content.decode()
        self.assertLess(
            html.index('data-open-dialog="crear-curso"'), html.index("course-grid")
        )
        self.assertContains(response, "<dialog", count=1)
        self.assertEqual(self.client.get(reverse("crear_curso")).status_code, 200)
        response = self.client.post(
            reverse("crear_curso"),
            {
                "asignatura": "Biología",
                "seccion": "C",
                "semestre_actual": 1,
                "anio_actual": 2027,
                "profesor": self.otro.pk,
            },
        )
        sala = Sala.objects.get(asignatura="Biología")
        self.assertEqual(sala.profesor, self.prof)
        self.assertRedirects(response, reverse("curso", args=[sala.pk]))

    def test_estudiante_no_puede_crear_y_formulario_invalido_conserva_errores(self):
        self.login()
        for method in [self.client.get, self.client.post]:
            self.assertEqual(method(reverse("crear_curso")).status_code, 403)
        self.login(self.prof)
        response = self.client.post(
            reverse("crear_curso"),
            {"asignatura": "", "semestre_actual": 3, "anio_actual": 2027},
        )
        self.assertTrue(response.context["form"].errors)
