from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import Calificacion, Estudiante, Materia, Sala, Tarea


class StudentCalendarTests(TestCase):
    def setUp(self):
        self.sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Historia',
        )
        self.estudiante = Estudiante.objects.create(
            nombre='Ana',
            apellido='Pérez',
            edad=15,
            tiempo_viaje='< 15 min',
            sala=self.sala,
        )
        self.materia = Materia.objects.create(nombre='Historia')
        self.client.post(
            reverse('usuario'),
            {
                'nombre_estudiante': self.estudiante.nombre,
                'apellido_estudiante': self.estudiante.apellido,
                'codigo_sala': self.sala.codigo,
            },
        )

    def test_calendar_button_and_assigned_task_deadlines_are_rendered(self):
        Tarea.objects.create(
            estudiante=self.estudiante,
            materia=self.materia,
            titulo='Ensayo de historia',
            fecha_entrega='2026-11-18',
        )
        otro_estudiante = Estudiante.objects.create(
            nombre='Luis',
            apellido='Gómez',
            edad=15,
            tiempo_viaje='< 15 min',
            sala=self.sala,
        )
        Tarea.objects.create(
            estudiante=otro_estudiante,
            materia=self.materia,
            titulo='Tarea de otro estudiante',
            fecha_entrega='2026-11-20',
        )
        Tarea.objects.create(
            estudiante=self.estudiante,
            materia=self.materia,
            titulo='Tarea ya completada',
            fecha_entrega='2026-11-22',
            completada=True,
        )

        response = self.client.get(reverse('usuario'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Calendario')
        self.assertNotContains(response, 'd-none" aria-label="Calendario de entregas"')
        self.assertContains(response, 'calendarPrevious')
        self.assertContains(response, 'calendarNext')
        self.assertContains(response, 'Ensayo de historia')
        self.assertContains(response, '2026-11-18')
        self.assertNotContains(response, 'Tarea de otro estudiante')
        self.assertNotContains(response, 'Tarea ya completada')
        self.assertNotContains(response, 'Próximas Tareas Pendientes')

    def test_student_login_saves_surname_for_new_student(self):
        response = self.client.post(
            reverse('usuario'),
            {
                'nombre_estudiante': 'Camila',
                'apellido_estudiante': 'Rojas',
                'codigo_sala': self.sala.codigo,
            },
        )

        self.assertRedirects(response, reverse('usuario'))
        estudiante = Estudiante.objects.get(nombre='Camila', sala=self.sala)
        self.assertEqual(estudiante.apellido, 'Rojas')

    def test_student_login_updates_legacy_default_surname(self):
        estudiante = Estudiante.objects.create(
            nombre='Diego',
            apellido='1',
            edad=15,
            tiempo_viaje='< 15 min',
            sala=self.sala,
        )

        response = self.client.post(
            reverse('usuario'),
            {
                'nombre_estudiante': 'Diego',
                'apellido_estudiante': 'Pérez',
                'codigo_sala': self.sala.codigo,
            },
        )

        self.assertRedirects(response, reverse('usuario'))
        estudiante.refresh_from_db()
        self.assertEqual(estudiante.apellido, 'Pérez')


class RoomTaskAssignmentTests(TestCase):
    @patch('AppEstudios.models.timezone.localdate', return_value=date(2026, 3, 10))
    def test_new_room_starts_in_semester_of_creation_date(self, _mock_localdate):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Matemáticas',
        )

        self.assertEqual((sala.semestre_actual, sala.anio_actual), (1, 2026))

    def test_ending_semester_requires_si_and_advances_only_active_room(self):
        sala_activa = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Matemáticas',
            semestre_actual=1,
            anio_actual=2025,
            semestre_inicio=1,
            anio_inicio=2025,
        )
        otra_sala = Sala.objects.create(
            nombre_profesor='Profesor Otro',
            asignatura='Historia',
            semestre_actual=2,
            anio_actual=2025,
            semestre_inicio=2,
            anio_inicio=2025,
        )
        session = self.client.session
        session['sala_activa_id'] = sala_activa.id
        session.save()

        response = self.client.post(
            reverse('administrador'),
            {'terminar_semestre': '1', 'confirmacion': 'no'},
            follow=True,
        )
        self.assertContains(response, 'Escribe SI para confirmar el cierre del semestre.')
        sala_activa.refresh_from_db()
        self.assertEqual((sala_activa.semestre_actual, sala_activa.anio_actual), (1, 2025))

        for expected_period in ((2, 2025), (1, 2026)):
            response = self.client.post(
                reverse('administrador'),
                {'terminar_semestre': '1', 'confirmacion': 'si'},
                follow=True,
            )
            self.assertRedirects(response, reverse('administrador'))
            sala_activa.refresh_from_db()
            self.assertEqual(
                (sala_activa.semestre_actual, sala_activa.anio_actual),
                expected_period,
            )

        otra_sala.refresh_from_db()
        self.assertEqual((otra_sala.semestre_actual, otra_sala.anio_actual), (2, 2025))
        self.assertContains(response, 'Terminar semestre · Semestre 1 2026')

    def test_ending_second_semester_advances_to_first_semester_next_year(self):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Matemáticas',
            semestre_actual=2,
            anio_actual=2026,
            semestre_inicio=2,
            anio_inicio=2026,
        )
        session = self.client.session
        session['sala_activa_id'] = sala.id
        session.save()

        self.client.post(
            reverse('administrador'),
            {'terminar_semestre': '1', 'confirmacion': 'SI'},
        )

        sala.refresh_from_db()
        self.assertEqual((sala.semestre_actual, sala.anio_actual), (1, 2027))

    def test_dashboard_can_browse_history_only_back_to_room_start(self):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Matemáticas',
            semestre_inicio=1,
            anio_inicio=2025,
            semestre_actual=1,
            anio_actual=2026,
        )
        estudiante = Estudiante.objects.create(
            nombre='Ana',
            apellido='Pérez',
            edad=15,
            tiempo_viaje='< 15 min',
            sala=sala,
        )
        materia = Materia.objects.create(nombre='Álgebra')
        Calificacion.objects.create(
            estudiante=estudiante,
            materia=materia,
            semestre=1,
            anio=2025,
            nota=4.0,
        )
        Calificacion.objects.create(
            estudiante=estudiante,
            materia=materia,
            semestre=2,
            anio=2025,
            nota=6.0,
        )
        Calificacion.objects.create(
            estudiante=estudiante,
            materia=materia,
            semestre=1,
            anio=2026,
            nota=7.0,
        )
        session = self.client.session
        session['sala_activa_id'] = sala.id
        session.save()

        response = self.client.get(reverse('administrador'))
        self.assertEqual(response.context['periodo_label'], 'Semestre 1 2026')
        self.assertContains(response, 'name="ver_semestre_anterior"')
        self.assertNotContains(response, 'name="volver_semestre_actual"')

        for expected_period, expected_average in (
            ('Semestre 2 2025', 6.0),
            ('Semestre 1 2025', 4.0),
        ):
            response = self.client.post(
                reverse('administrador'),
                {'ver_semestre_anterior': '1'},
                follow=True,
            )
            self.assertEqual(response.context['periodo_label'], expected_period)
            self.assertEqual(response.context['kpi_promedio_general'], expected_average)
            self.assertContains(response, 'name="volver_semestre_actual"')

        self.assertContains(response, 'name="ver_semestre_anterior" value="1" class="btn btn-outline-secondary fw-bold" disabled')
        self.client.post(
            reverse('administrador'),
            {'ver_semestre_anterior': '1'},
            follow=True,
        )
        response = self.client.get(reverse('administrador'))
        self.assertEqual(response.context['periodo_label'], 'Semestre 1 2025')

        response = self.client.post(
            reverse('administrador'),
            {'volver_semestre_actual': '1'},
            follow=True,
        )
        self.assertEqual(response.context['periodo_label'], 'Semestre 1 2026')
        self.assertEqual(response.context['kpi_promedio_general'], 7.0)

    def test_dashboard_filters_grades_to_active_room_semester_and_year(self):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Matemáticas',
            semestre_actual=1,
            anio_actual=2025,
            semestre_inicio=1,
            anio_inicio=2025,
        )
        estudiante = Estudiante.objects.create(
            nombre='Ana',
            apellido='Pérez',
            edad=15,
            tiempo_viaje='< 15 min',
            sala=sala,
        )
        materia = Materia.objects.create(nombre='Álgebra')
        Calificacion.objects.create(
            estudiante=estudiante,
            materia=materia,
            semestre=1,
            anio=2025,
            nota=4.0,
        )
        Calificacion.objects.create(
            estudiante=estudiante,
            materia=materia,
            semestre=2,
            anio=2025,
            nota=7.0,
        )
        session = self.client.session
        session['sala_activa_id'] = sala.id
        session.save()

        response = self.client.get(reverse('administrador'))

        self.assertContains(response, 'Terminar semestre · Semestre 1 2025')
        self.assertEqual(response.context['kpi_promedio_general'], 4.0)
        self.assertEqual(response.context['g4_labels'], ['Álgebra'])
        self.assertEqual(response.context['g3_labels'], ['Semestre 1 2025'])
        self.assertEqual(response.context['g3_data'], [4.0])

    def test_new_grade_uses_active_room_academic_period(self):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Matemáticas',
            semestre_actual=2,
            anio_actual=2025,
            semestre_inicio=1,
            anio_inicio=2025,
        )
        estudiante = Estudiante.objects.create(
            nombre='Ana',
            apellido='Pérez',
            edad=15,
            tiempo_viaje='< 15 min',
            sala=sala,
        )
        session = self.client.session
        session['sala_activa_id'] = sala.id
        session.save()

        response = self.client.post(
            reverse('administrador'),
            {
                'crear_nota': '1',
                'estudiante_id': estudiante.id,
                'materia_nombre': 'Álgebra',
                'nota': '6.5',
            },
        )

        self.assertRedirects(response, reverse('administrador'))
        calificacion = Calificacion.objects.get(estudiante=estudiante)
        self.assertEqual((calificacion.semestre, calificacion.anio), (2, 2025))

    def test_admin_dashboard_has_no_student_creation_option(self):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Matemáticas',
        )
        session = self.client.session
        session['sala_activa_id'] = sala.id
        session.save()

        response = self.client.get(reverse('administrador'))

        self.assertNotContains(response, 'crear_estudiante')
        self.assertNotContains(response, 'Agregar Alumno')
        self.assertNotContains(response, 'Guardar Alumno')

    def test_admin_dashboard_does_not_create_students_from_post(self):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Matemáticas',
        )
        session = self.client.session
        session['sala_activa_id'] = sala.id
        session.save()

        response = self.client.post(
            reverse('administrador'),
            {
                'crear_estudiante': '1',
                'nombre': 'Ana',
                'apellido': 'Pérez',
                'edad': '16',
                'tiempo_viaje': '31 min - 1 hora',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Estudiante.objects.filter(nombre='Ana', sala=sala).exists())

    def test_student_listing_shows_surname_instead_of_age(self):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Matemáticas',
        )
        Estudiante.objects.create(
            nombre='Ana',
            apellido='Pérez',
            edad=15,
            tiempo_viaje='< 15 min',
            sala=sala,
        )
        session = self.client.session
        session['sala_activa_id'] = sala.id
        session.save()

        response = self.client.get(reverse('administrador'))
        student_table = response.content.decode().split(
            '<h5 class="fw-bold mb-1">Listado de Alumnos',
            1,
        )[1].split('</table>', 1)[0]

        self.assertIn('<th>Apellido</th>', student_table)
        self.assertNotIn('<th>Edad</th>', student_table)
        self.assertNotIn('Tiempo de Viaje', student_table)
        self.assertIn('<td>Pérez</td>', student_table)
        self.assertNotIn('<td>15 años</td>', student_table)

    def test_task_is_assigned_to_every_student_in_active_room_only(self):
        sala_activa = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Historia',
        )
        sala_ajena = Sala.objects.create(
            nombre_profesor='Profesor Otro',
            asignatura='Matemáticas',
        )
        estudiantes_activos = [
            Estudiante.objects.create(
                nombre=nombre,
                apellido='Alumno',
                edad=15,
                tiempo_viaje='< 15 min',
                sala=sala_activa,
            )
            for nombre in ('Ana', 'Luis')
        ]
        estudiante_ajeno = Estudiante.objects.create(
            nombre='Sofía',
            apellido='Alumno',
            edad=15,
            tiempo_viaje='< 15 min',
            sala=sala_ajena,
        )
        session = self.client.session
        session['sala_activa_id'] = sala_activa.id
        session.save()

        response = self.client.post(
            reverse('administrador'),
            {
                'crear_tarea': '1',
                'titulo': 'Trabajo de investigación',
                'fecha_entrega': '25/11/2026',
            },
        )

        self.assertRedirects(response, reverse('administrador'))
        self.assertEqual(Tarea.objects.count(), len(estudiantes_activos))
        self.assertSetEqual(
            set(Tarea.objects.values_list('estudiante_id', flat=True)),
            {estudiante.id for estudiante in estudiantes_activos},
        )
        tarea = Tarea.objects.first()
        self.assertEqual(tarea.fecha_entrega.isoformat(), '2026-11-25')
        self.assertEqual(tarea.materia.nombre, sala_activa.asignatura)
        self.assertFalse(Tarea.objects.filter(estudiante=estudiante_ajeno).exists())

    def test_assignment_form_does_not_ask_for_student_or_subject(self):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Historia',
        )
        session = self.client.session
        session['sala_activa_id'] = sala.id
        session.save()

        response = self.client.get(reverse('administrador'))
        task_modal = response.content.decode().split('id="modalNuevaTarea"', 1)[1]
        task_modal = task_modal.split('<!-- Bootstrap JS Bundle -->', 1)[0]

        self.assertContains(response, 'La tarea se asignará a todos los alumnos de la sala activa')
        self.assertNotIn('name="estudiante_id"', task_modal)
        self.assertNotIn('name="materia_nombre"', task_modal)
        self.assertIn('placeholder="DD/MM/AAAA"', task_modal)

    def test_invalid_deadline_format_shows_validation_error(self):
        sala = Sala.objects.create(
            nombre_profesor='Profesora Ejemplo',
            asignatura='Historia',
        )
        estudiante = Estudiante.objects.create(
            nombre='Ana',
            apellido='Pérez',
            edad=15,
            tiempo_viaje='< 15 min',
            sala=sala,
        )
        session = self.client.session
        session['sala_activa_id'] = sala.id
        session.save()

        response = self.client.post(
            reverse('administrador'),
            {
                'crear_tarea': '1',
                'titulo': 'Trabajo de investigación',
                'fecha_entrega': '2026-11-25',
            },
            follow=True,
        )

        self.assertContains(response, 'Ingresa una fecha válida en formato DD/MM/AAAA.')
        self.assertFalse(Tarea.objects.filter(estudiante=estudiante).exists())
