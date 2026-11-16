"""Integration tests for authenticated, course-scoped student/teacher flows."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from ..models import Sala, Estudiante, Inscripcion, Materia, Calificacion


class PortalTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.prof = User.objects.create_user("docente", password="clave")
        cls.otro = User.objects.create_user("otro_docente", password="clave")
        grupo = Group.objects.create(name="Profesores")
        cls.prof.groups.add(grupo)
        cls.otro.groups.add(grupo)
        cls.user = User.objects.create_user("ana", password="clave")
        cls.est = Estudiante.objects.create(
            usuario=cls.user,
            nombre="Ana",
            apellido="Pérez",
            edad=20,
            tiempo_viaje="< 15 min",
        )
        cls.user2 = User.objects.create_user("luis", password="clave")
        cls.est2 = Estudiante.objects.create(
            usuario=cls.user2,
            nombre="Luis",
            apellido="Rojas",
            edad=21,
            tiempo_viaje="< 15 min",
        )
        cls.a = Sala.objects.create(
            profesor=cls.prof,
            nombre_profesor="Docente",
            asignatura="Álgebra",
            seccion="A",
            semestre_actual=2,
            anio_actual=2026,
            semestre_inicio=1,
            anio_inicio=2025,
        )
        cls.b = Sala.objects.create(
            profesor=cls.prof,
            nombre_profesor="Docente",
            asignatura="Álgebra",
            seccion="B",
            semestre_actual=1,
            anio_actual=2026,
        )
        cls.c = Sala.objects.create(
            profesor=cls.otro, nombre_profesor="Otro", asignatura="Historia"
        )
        Inscripcion.objects.create(estudiante=cls.est, sala=cls.a)
        Inscripcion.objects.create(estudiante=cls.est, sala=cls.b)
        Inscripcion.objects.create(estudiante=cls.est2, sala=cls.c)
        cls.m = Materia.objects.create(nombre="Álgebra")

    def url(self, curso=None, seccion=None):
        return (
            reverse("curso_seccion", args=[(curso or self.a).pk, seccion])
            if seccion
            else reverse("curso", args=[(curso or self.a).pk])
        )

    def login(self, user=None):
        self.client.force_login(user or self.user)

    def nota(self, curso, valor, semestre=2, anio=2026, estudiante=None):
        return Calificacion.objects.create(
            sala=curso,
            estudiante=estudiante or self.est,
            materia=self.m,
            nota=valor,
            semestre=semestre,
            anio=anio,
        )
