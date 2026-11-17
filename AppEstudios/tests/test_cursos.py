"""Pruebas de cursos en el flujo autenticado por curso."""

from datetime import date
from django.urls import reverse
from ..models import Sala, Calificacion, Tarea


from .base import PortalTestCase


class CursosTests(PortalTestCase):
    def test_students_averages_are_scoped_to_course_and_period(self):
        from ..models import Inscripcion

        Inscripcion.objects.create(estudiante=self.est2, sala=self.a)
        self.nota(self.a, 4)
        self.nota(self.a, 6)
        self.nota(self.a, 1, semestre=1)
        self.nota(self.a, 2, anio=2025)
        self.nota(self.b, 7)
        self.login(self.prof)
        response = self.client.get(
            self.url(self.a, "estudiantes"), {"semestre": 2, "anio": 2026}
        )
        self.assertEqual(response.status_code, 200)
        alumnos = {a.pk: a for a in response.context["alumnos"]}
        self.assertEqual(alumnos[self.est.pk].promedio_periodo, 5)
        self.assertEqual(alumnos[self.est.pk].cantidad_notas, 2)
        self.assertIsNone(alumnos[self.est2.pk].promedio_periodo)
        self.assertEqual(alumnos[self.est2.pk].cantidad_notas, 0)
        self.assertContains(response, "Sin notas")
        self.assertContains(response, "student-profile")

    def test_board_has_enrolled_courses_without_grades(self):
        self.login()
        response = self.client.get(reverse("tablero"))
        self.assertEqual(len(response.context["tarjetas"]), 2)
        self.assertNotContains(response, "Historia")
        self.assertContains(response, self.url(self.a))
        self.assertContains(response, self.url(self.b))

    def test_teacher_board_only_owned_courses_and_codes(self):
        self.login(self.prof)
        response = self.client.get(reverse("tablero"))
        self.assertEqual(len(response.context["tarjetas"]), 2)
        self.assertContains(response, self.a.codigo)
        self.assertNotContains(response, self.c.codigo)

    def test_create_multiple_sections(self):
        self.login(self.prof)
        for section in ["C", "D"]:
            response = self.client.post(
                reverse("tablero"),
                {
                    "asignatura": "Álgebra",
                    "seccion": section,
                    "semestre_actual": 1,
                    "anio_actual": 2027,
                    "profesor": self.otro.pk,
                },
            )
            self.assertEqual(response.status_code, 302)
        courses = Sala.objects.filter(seccion__in=["C", "D"])
        self.assertEqual(courses.count(), 2)
        self.assertEqual(len(set(courses.values_list("codigo", flat=True))), 2)
        self.assertTrue(
            all(c.profesor == self.prof and c.anio_inicio == 2027 for c in courses)
        )

    def test_student_cannot_create_course(self):
        self.login()
        self.assertEqual(
            self.client.post(reverse("tablero"), {"asignatura": "Intruso"}).status_code,
            403,
        )

    def test_course_permissions_all_sections(self):
        for user in [self.user, self.prof]:
            self.login(user)
            for section in [
                "resumen",
                "estudiantes",
                "calificaciones",
                "habitos",
                "tareas",
                "configuracion",
            ]:
                self.assertEqual(
                    self.client.get(self.url(self.c, section)).status_code, 404
                )
                self.assertEqual(
                    self.client.post(
                        self.url(self.c, section),
                        {"crear_nota": "", "tipo_evaluacion": "certamen_1", "nota": 7, "estudiante": self.est.pk},
                    ).status_code,
                    404,
                )
        self.login()
        for section in ["estudiantes", "habitos", "configuracion"]:
            self.assertEqual(
                self.client.get(self.url(self.a, section)).status_code, 403
            )

    def test_student_cannot_write_teacher_forms(self):
        self.login()
        self.assertEqual(
            self.client.post(
                self.url(self.a, "calificaciones"),
                {"crear_nota": "", "tipo_evaluacion": "certamen_1", "estudiante": self.est.pk, "nota": 7},
            ).status_code,
            403,
        )
        self.assertFalse(Calificacion.objects.exists())

    def test_grade_validates_membership_range_and_finite(self):
        self.login(self.prof)
        for valor in ["0.9", "7.1", "NaN", "Infinity", "texto"]:
            response = self.client.post(
                self.url(self.a, "calificaciones"),
                {"crear_nota": "", "tipo_evaluacion": "certamen_1", "estudiante": self.est.pk, "nota": valor},
            )
            self.assertTrue(response.context["nota_form"].errors)
        self.client.post(
            self.url(self.a, "calificaciones"),
            {"crear_nota": "", "tipo_evaluacion": "certamen_1", "estudiante": self.est2.pk, "nota": 6},
        )
        self.assertFalse(Calificacion.objects.exists())

    def test_multitab_notes_and_tasks_bind_to_url(self):
        self.login(self.prof)
        self.client.get(self.url(self.a))
        self.client.get(self.url(self.b))
        session = self.client.session
        session["sala_activa_id"] = self.c.pk
        session.save()
        for curso in [self.a, self.b]:
            self.client.post(
                self.url(curso, "calificaciones"),
                {
                    "crear_nota": "", "tipo_evaluacion": "certamen_1",
                    "estudiante": self.est.pk,
                    "nota": "6,5",
                    "materia": "Falsa",
                    "sala_id": self.c.pk,
                },
            )
            self.client.post(
                self.url(curso, "tareas"),
                {
                    "crear_tarea": "",
                    "titulo": "Entrega " + curso.seccion,
                    "fecha_entrega": "2026-11-18",
                    "sala_id": self.c.pk,
                },
            )
            nota = curso.calificaciones.get()
            self.assertEqual(
                (nota.semestre, nota.anio, nota.materia.nombre, nota.nota),
                (curso.semestre_actual, curso.anio_actual, curso.asignatura, 6.5),
            )
            self.assertEqual(curso.tareas.get().titulo, "Entrega " + curso.seccion)
        self.assertFalse(self.c.tareas.exists())

    def test_close_semester_preserves_grades_and_prevents_stale_double_close(self):
        self.login(self.prof)
        old = self.nota(self.a, 5)
        url = self.url(self.a, "configuracion")
        self.client.post(
            url,
            {"terminar_semestre": "", "confirmacion": "no", "periodo_actual": "2-2026"},
        )
        self.a.refresh_from_db()
        self.assertEqual(self.a.semestre_actual, 2)
        for _ in range(2):
            self.client.post(
                url,
                {
                    "terminar_semestre": "",
                    "confirmacion": "SI",
                    "periodo_actual": "2-2026",
                },
            )
        self.a.refresh_from_db()
        self.assertEqual((self.a.semestre_actual, self.a.anio_actual), (1, 2027))
        self.assertTrue(Calificacion.objects.filter(pk=old.pk).exists())
        response = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2026}
        )
        self.assertEqual(list(response.context["notas"]), [old])
        self.b.refresh_from_db()
        self.assertEqual(self.b.semestre_actual, 1)

    def test_periods_and_student_privacy(self):
        old = self.nota(self.a, 2, anio=2025)
        current = self.nota(self.a, 6)
        self.nota(self.a, 1, estudiante=self.est2)
        self.login()
        response = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2026}
        )
        self.assertEqual(list(response.context["notas"]), [current])
        response = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2025}
        )
        self.assertEqual(list(response.context["notas"]), [old])

    def test_student_fiche_scoped_to_membership(self):
        self.login(self.prof)
        self.assertEqual(
            self.client.get(
                reverse("ficha_estudiante", args=[self.a.pk, self.est2.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("ficha_estudiante", args=[self.a.pk, self.est.pk])
            ).status_code,
            200,
        )
        self.login()
        self.assertEqual(
            self.client.get(
                reverse("ficha_estudiante", args=[self.a.pk, self.est.pk])
            ).status_code,
            403,
        )

    def test_teacher_all_pages_and_invalid_filters_render(self):
        self.login(self.prof)
        for section in [
            "resumen",
            "estudiantes",
            "calificaciones",
            "habitos",
            "tareas",
            "configuracion",
        ]:
            self.assertEqual(
                self.client.get(
                    self.url(self.a, section), {"semestre": "abc", "anio": "-3"}
                ).status_code,
                200,
            )
        self.assertEqual(self.client.get(reverse("rendimiento")).status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("calendario"), {"mes": "mal", "anio": 99999}
            ).status_code,
            200,
        )

    def test_grade_boundaries(self):
        self.login(self.prof)
        for nota in ["1,0", "7,0"]:
            response = self.client.post(
                self.url(self.a, "calificaciones"),
                {"crear_nota": "", "tipo_evaluacion": "certamen_1", "estudiante": self.est.pk, "nota": nota},
            )
            self.assertEqual(response.status_code, 302)
        self.assertEqual(
            set(self.a.calificaciones.values_list("nota", flat=True)), {1.0, 7.0}
        )

    def test_evaluation_is_selected_and_saved(self):
        self.login(self.prof)
        for tipo in ["certamen_1", "certamen_2", "control"]:
            response = self.client.post(self.url(self.a, "calificaciones"), {
                "crear_nota": "", "estudiante": self.est.pk,
                "nota": "5,5", "tipo_evaluacion": tipo,
            })
            self.assertEqual(response.status_code, 302)
            self.assertTrue(self.a.calificaciones.filter(tipo_evaluacion=tipo).exists())
        for tipo in ["", "Evaluación inventada"]:
            response = self.client.post(self.url(self.a, "calificaciones"), {
                "crear_nota": "", "estudiante": self.est.pk,
                "nota": "5,5", "tipo_evaluacion": tipo,
            })
            self.assertIn("tipo_evaluacion", response.context["nota_form"].errors)
        self.assertEqual(self.a.calificaciones.count(), 3)
        self.login()
        response = self.client.get(self.url(self.a, "calificaciones"))
        self.assertContains(response, "Certamen 1")
        self.assertContains(response, "Certamen 2")
        self.assertContains(response, "Control")

    def test_close_first_semester(self):
        self.login(self.prof)
        self.client.post(
            self.url(self.b, "configuracion"),
            {"terminar_semestre": "", "confirmacion": "SI", "periodo_actual": "1-2026"},
        )
        self.b.refresh_from_db()
        self.assertEqual((self.b.semestre_actual, self.b.anio_actual), (2, 2026))

    def test_student_private_tasks_are_not_visible_to_classmates(self):
        Tarea.objects.create(
            sala=self.a,
            estudiante=self.est2,
            materia=self.m,
            titulo="Privada de Luis",
            fecha_entrega=date(2026, 11, 18),
        )
        self.login()
        self.assertNotContains(
            self.client.get(self.url(self.a, "tareas")), "Privada de Luis"
        )

    def test_course_tabs_keep_selected_period(self):
        self.login()
        response = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 1, "anio": 2025}
        )
        self.assertContains(
            response, self.url(self.a, "resumen") + "?semestre=1&anio=2025"
        )
