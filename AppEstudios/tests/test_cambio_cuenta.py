"""Cambiar la identidad autenticada, conservando cuentas y permisos separados."""

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from ..models import Estudiante, Sala
from .base import PortalTestCase


class CambioCuentaTests(PortalTestCase):
    def entrar(self, usuario, clave="clave"):
        return self.client.post(
            reverse("cambiar_cuenta"), {"username": usuario.username, "password": clave}
        )

    def test_cambiar_profesor_estudiante_y_volver_no_mezcla_perfiles(self):
        self.login(self.prof)
        grupos_antes = list(self.prof.groups.values_list("name", flat=True))
        response = self.client.get(reverse("cambiar_cuenta"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.prof.username)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.prof.pk))
        response = self.entrar(self.user)
        self.assertRedirects(
            response, reverse("mi_cuenta"), fetch_redirect_response=False
        )
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        tablero = self.client.get(reverse("tablero"))
        self.assertFalse(tablero.context["profesor"])
        self.assertEqual(len(tablero.context["tarjetas"]), 2)
        self.assertEqual(self.client.post(reverse("crear_curso")).status_code, 403)
        self.assertEqual(self.client.get(self.url(self.c)).status_code, 404)
        self.entrar(self.prof)
        tablero = self.client.get(reverse("tablero"))
        self.assertTrue(tablero.context["profesor"])
        self.assertEqual(len(tablero.context["tarjetas"]), 2)
        self.assertEqual(
            list(self.prof.groups.values_list("name", flat=True)), grupos_antes
        )
        self.assertFalse(Estudiante.objects.filter(usuario=self.prof).exists())
        self.assertEqual(Estudiante.objects.get(usuario=self.user).pk, self.est.pk)
        self.assertEqual(Sala.objects.filter(profesor=self.prof).count(), 2)
        self.assertFalse(self.user.groups.exists())

    def test_credenciales_invalidas_conservan_cuenta_actual(self):
        self.login(self.prof)
        response = self.entrar(self.user, clave="incorrecta")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.prof.pk))
        self.assertTrue(self.client.get(reverse("tablero")).context["profesor"])

    def test_ingresar_no_redirige_al_usuario_que_quiere_otra_cuenta(self):
        self.login(self.prof)
        self.assertEqual(self.client.get(reverse("ingresar")).status_code, 200)
        response = self.client.post(
            reverse("ingresar"), {"username": self.user.username, "password": "clave"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))
        self.assertEqual(
            self.client.post(
                self.url(self.a, "calificaciones"),
                {"crear_nota": "", "estudiante": self.est.pk, "nota": 7},
            ).status_code,
            403,
        )

    def test_valores_antiguos_de_sesion_no_permiten_cambiar_rol(self):
        for usuario, rol_falso, profesor in [
            (self.user, "profesor", False),
            (self.prof, "estudiante", True),
        ]:
            self.login(usuario)
            session = self.client.session
            session["vista_prueba"] = rol_falso
            session.save()
            response = self.client.get(reverse("tablero"))
            self.assertEqual(response.context["profesor"], profesor)
            self.assertNotContains(response, "role-switch")
            self.assertContains(response, reverse("cambiar_cuenta"))

    def test_endpoint_antiguo_ya_no_crea_perfiles_ni_concede_acceso(self):
        self.login(self.prof)
        self.assertEqual(
            self.client.post(
                "/cambiar-vista/",
                {
                    "rol": "estudiante",
                    "completar_perfil": 1,
                    "edad": 20,
                    "tiempo_viaje": "< 15 min",
                },
            ).status_code,
            404,
        )
        self.assertFalse(Estudiante.objects.filter(usuario=self.prof).exists())
        self.assertEqual(self.client.session["_auth_user_id"], str(self.prof.pk))

    def test_cambio_de_cuenta_requiere_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.prof)
        self.assertEqual(
            client.post(
                reverse("cambiar_cuenta"),
                {"username": self.user.username, "password": "clave"},
            ).status_code,
            403,
        )
        self.assertEqual(client.session["_auth_user_id"], str(self.prof.pk))

    def test_crear_segunda_cuenta_no_modifica_la_cuenta_original(self):
        self.login(self.prof)
        self.assertEqual(self.client.get(reverse("registrarse")).status_code, 200)
        response = self.client.post(
            reverse("registrarse"),
            {
                "username": "estudiante_independiente",
                "first_name": "Nueva",
                "last_name": "Cuenta",
                "rol": "estudiante",
                "edad": 20,
                "tiempo_viaje": "< 15 min",
                "password1": "Cuenta-Segura-2026",
                "password2": "Cuenta-Segura-2026",
            },
        )
        self.assertEqual(response.status_code, 302)
        nueva = get_user_model().objects.get(username="estudiante_independiente")
        self.assertNotEqual(nueva.pk, self.prof.pk)
        self.assertEqual(self.client.session["_auth_user_id"], str(nueva.pk))
        self.assertTrue(Estudiante.objects.filter(usuario=nueva).exists())
        self.assertFalse(Estudiante.objects.filter(usuario=self.prof).exists())
        self.assertTrue(self.prof.groups.filter(name="Profesores").exists())
        self.assertEqual(Sala.objects.filter(profesor=self.prof).count(), 2)

    def test_sesiones_independientes_mantienen_cuentas_distintas(self):
        profesor = Client()
        estudiante = Client()
        profesor.force_login(self.prof)
        estudiante.force_login(self.user)
        self.assertTrue(profesor.get(reverse("tablero")).context["profesor"])
        self.assertFalse(estudiante.get(reverse("tablero")).context["profesor"])
        self.assertEqual(profesor.session["_auth_user_id"], str(self.prof.pk))
        self.assertEqual(estudiante.session["_auth_user_id"], str(self.user.pk))

    def test_perfil_heredado_no_convierte_profesor_en_cuenta_estudiante(self):
        legado = Estudiante.objects.create(
            usuario=self.prof,
            nombre="Legado",
            apellido="Conservado",
            edad=20,
            tiempo_viaje="< 15 min",
        )
        self.login(self.prof)
        self.assertEqual(self.client.get(reverse("estudio")).status_code, 403)
        self.assertEqual(
            self.client.post(
                reverse("inscribirse"), {"codigo_sala": self.a.codigo}
            ).status_code,
            403,
        )
        self.assertTrue(Estudiante.objects.filter(pk=legado.pk).exists())
        self.assertTrue(self.client.get(reverse("tablero")).context["profesor"])
