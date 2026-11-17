"""Pruebas de migraciones en el flujo autenticado por curso."""

from datetime import date
from django.test import TransactionTestCase
from django.db.migrations.executor import MigrationExecutor
from django.db import connection


class StudyMigrationTests(TransactionTestCase):
    def test_legacy_study_and_personal_tasks_are_preserved(self):
        executor = MigrationExecutor(connection)
        before = [("AppEstudios", "0010_conservar_inscripciones_existentes")]
        after = [
            (
                "AppEstudios",
                "0011_remove_registroestudio_estudio_unico_por_dia_and_more",
            )
        ]
        executor.migrate(before)
        apps = executor.loader.project_state(before).apps
        est = apps.get_model("AppEstudios", "Estudiante").objects.create(
            nombre="Histórico", apellido="Conservado", edad=20, tiempo_viaje="< 15 min"
        )
        registro = apps.get_model("AppEstudios", "RegistroEstudio").objects.create(
            estudiante_id=est.pk, fecha=date(2026, 1, 1), minutos=83
        )
        materia = apps.get_model("AppEstudios", "Materia").objects.create(
            nombre="Anterior"
        )
        tarea = apps.get_model("AppEstudios", "Tarea").objects.create(
            estudiante_id=est.pk,
            materia_id=materia.pk,
            titulo="Tarea hist?rica",
            fecha_entrega=date(2026, 1, 2),
            completada=True,
        )
        try:
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            apps = executor.loader.project_state(after).apps
            saved = apps.get_model("AppEstudios", "RegistroEstudio").objects.get(
                pk=registro.pk
            )
            self.assertEqual(saved.minutos, 83)
            self.assertIsNone(saved.sala_id)
            saved_task = apps.get_model("AppEstudios", "Tarea").objects.get(pk=tarea.pk)
            self.assertEqual(saved_task.estudiante_id, est.pk)
            self.assertTrue(saved_task.completada)
        finally:
            MigrationExecutor(connection).migrate(
                MigrationExecutor(connection).loader.graph.leaf_nodes()
            )
