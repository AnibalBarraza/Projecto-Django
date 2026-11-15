from django.db import migrations


def conservar_relaciones(apps, schema_editor):
    Estudiante = apps.get_model("AppEstudios", "Estudiante")
    Inscripcion = apps.get_model("AppEstudios", "Inscripcion")
    Calificacion = apps.get_model("AppEstudios", "Calificacion")
    Tarea = apps.get_model("AppEstudios", "Tarea")

    alias = schema_editor.connection.alias

    estudiantes = (
        Estudiante.objects.using(alias)
        .exclude(sala_id=None)
        .iterator()
    )

    for estudiante in estudiantes:
        Inscripcion.objects.using(alias).get_or_create(
            estudiante_id=estudiante.pk,
            sala_id=estudiante.sala_id,
        )

        for modelo in (Calificacion, Tarea):
            (
                modelo.objects.using(alias)
                .filter(
                    estudiante_id=estudiante.pk,
                    sala_id=None,
                )
                .update(sala_id=estudiante.sala_id)
            )


class Migration(migrations.Migration):
    dependencies = [
        ("AppEstudios", "0009_base_cursos_inscripciones"),
    ]

    operations = [
        migrations.RunPython(
            conservar_relaciones,
            migrations.RunPython.noop,
        ),
    ]