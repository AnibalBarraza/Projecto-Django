"""Crea un conjunto identificado de cuentas y datos ficticios, sin tocar los existentes."""

from datetime import timedelta
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from AppEstudios.models import (
    Calificacion, Estudiante, Inscripcion, Materia, RegistroEstudio, Sala, Tarea,
)


class Command(BaseCommand):
    help = "Agrega 2 profesores, 16 estudiantes y 4 cursos ficticios (usuarios demo_*)."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(username__startswith="demo_").exists():
            raise CommandError("Ya existen usuarios demo_*. No se cambió ningún dato.")
        password = "Demo-" + secrets.token_hex(6)
        hoy = timezone.localdate()
        semestre = 1 if hoy.month <= 6 else 2
        actual = hoy.year * 2 + semestre - 1
        periodos = [(p // 2, p % 2 + 1) for p in range(actual - 2, actual + 1)]
        grupo, _ = Group.objects.get_or_create(name="Profesores")
        profesores = []
        for i, nombre in enumerate(["Camila", "Diego"], 1):
            usuario = User.objects.create_user(
                f"demo_profe_{i}", password=password,
                first_name=nombre, last_name="",
            )
            usuario.groups.add(grupo)
            profesores.append(usuario)
        cursos = []
        for i, nombre in enumerate(["Matemáticas", "Física", "Lenguaje", "Historia"]):
            profesor = profesores[i // 2]
            curso = Sala.objects.create(
                profesor=profesor, nombre_profesor=profesor.get_full_name(),
                asignatura=nombre + " (Demo)", seccion="A",
                semestre_actual=semestre, anio_actual=hoy.year,
                anio_inicio=periodos[0][0], semestre_inicio=periodos[0][1],
            )
            materia = Materia.objects.create(nombre=nombre + " (Demo)")
            cursos.append((curso, materia))
            for j, dias in enumerate([-4, 2, 7, 14]):
                Tarea.objects.create(
                    sala=curso, materia=materia,
                    titulo=f"[Demo] {['Guía de repaso', 'Ejercicios', 'Trabajo práctico', 'Proyecto'][j]}",
                    fecha_entrega=hoy + timedelta(days=dias),
                )
        nombres = ["Ana", "Luis", "Sofía", "Tomás", "Valentina", "Mateo", "Isidora", "Lucas",
                   "Martina", "Benjamín", "Florencia", "Gabriel", "Emilia", "Vicente", "Antonia", "Nicolás"]
        notas = []
        registros = []
        for i, nombre in enumerate(nombres):
            usuario = User.objects.create_user(
                f"demo_estudiante_{i + 1:02d}", password=password,
                first_name=nombre, last_name="",
            )
            estudiante = Estudiante.objects.create(
                usuario=usuario, nombre=nombre, apellido="",
                edad=18 + i % 7, tiempo_viaje=Estudiante.TIEMPO_VIAJE_CHOICES[i % 4][0],
                meta_semanal_minutos=240 + (i % 3) * 60,
            )
            for c, (curso, materia) in enumerate(cursos):
                Inscripcion.objects.create(estudiante=estudiante, sala=curso)
                # Un inscrito sin notas permite explorar también ese estado.
                if i != 15:
                    for p, (anio, sem) in enumerate(periodos):
                        for n in range(3 + i % 3):
                            nota = max(1, min(7, 1.5 + (i % 11) * .48 + c * .15 + p * .2 + (n % 3 - 1) * .4))
                            notas.append(Calificacion(
                                estudiante=estudiante, sala=curso, materia=materia,
                                semestre=sem, anio=anio, nota=round(nota, 1),
                            ))
                for d in range(28):
                    if (d + i + c) % 3 == 0:
                        registros.append(RegistroEstudio(
                            estudiante=estudiante, sala=curso,
                            fecha=hoy - timedelta(days=d), minutos=15 + (i + d + c) % 6 * 10,
                        ))
            for d in range(0, 28, 4):
                registros.append(RegistroEstudio(
                    estudiante=estudiante, fecha=hoy - timedelta(days=d), minutos=20 + i % 4 * 10,
                ))
        Calificacion.objects.bulk_create(notas)
        RegistroEstudio.objects.bulk_create(registros)
        self.stdout.write(self.style.SUCCESS("Creados 2 profesores, 16 estudiantes, 4 cursos y 16 tareas Demo."))
        self.stdout.write("Notas de tres semestres y registros de estudio de las últimas cuatro semanas.")
        self.stdout.write(f"Contraseña común de las cuentas ficticias: {password}")
        self.stdout.write("Profesores: demo_profe_1, demo_profe_2")
        self.stdout.write("Estudiantes: demo_estudiante_01 a demo_estudiante_16")
