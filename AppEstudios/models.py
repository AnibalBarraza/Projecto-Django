import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings

def semestre_actual_por_fecha():
    return 1 if timezone.localdate().month <= 6 else 2


def anio_actual_por_fecha():
    return timezone.localdate().year

class Sala(models.Model):
    nombre_profesor = models.CharField(max_length=100)
    asignatura = models.CharField(max_length=100)
    codigo = models.CharField(max_length=10, unique=True, editable=False)
    semestre_actual = models.PositiveSmallIntegerField(default=semestre_actual_por_fecha)
    anio_actual = models.PositiveSmallIntegerField(default=anio_actual_por_fecha)
    semestre_inicio = models.PositiveSmallIntegerField(default=semestre_actual_por_fecha)
    anio_inicio = models.PositiveSmallIntegerField(default=anio_actual_por_fecha)
    profesor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cursos_impartidos",
        null=True,
        blank=True,
    )
    seccion = models.CharField(max_length=50, blank=True)
    archivada = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = uuid.uuid4().hex[:6].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asignatura} - Prof. {self.nombre_profesor} (Código: {self.codigo})"

class Estudiante(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    edad = models.IntegerField()
    meta_semanal_minutos = models.PositiveIntegerField(default=300)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="perfil_estudiante",
        null=True,
        blank=True,
    )
    cursos = models.ManyToManyField(
        Sala,
        through="Inscripcion",
        related_name="alumnos_inscritos",
    )
    TIEMPO_VIAJE_CHOICES = [
        ('< 15 min', 'Menos de 15 minutos'),
        ('15-30 min', 'Entre 15 y 30 minutos'),
        ('31 min - 1 hora', 'Entre 31 minutos y 1 hora'),
        ('> 1 hora', 'Más de 1 hora'),
    ]
    tiempo_viaje = models.CharField(max_length=50, choices=TIEMPO_VIAJE_CHOICES)
    sala = models.ForeignKey(Sala, on_delete=models.CASCADE, related_name="estudiantes", null=True, blank=True)

    def __str__(self):
        sala_info = f" ({self.sala.codigo})" if self.sala else ""
        return f"{self.nombre}{sala_info}"

class Materia(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Calificacion(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    semestre = models.IntegerField(help_text="Ejemplo: 1 o 2")
    anio = models.IntegerField(default=2025)
    nota = models.FloatField()
    sala = models.ForeignKey(
        Sala,
        on_delete=models.PROTECT,
        related_name="calificaciones",
        null=True,
        blank=True,
    )
    class Meta:
        indexes = [models.Index(fields=['sala', 'anio', 'semestre'], name='nota_curso_periodo_idx')]

    def __str__(self):
        return f"{self.estudiante.nombre} - {self.materia.nombre}: {self.nota}"

class Tarea(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, null=True, blank=True)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    fecha_entrega = models.DateField()
    completada = models.BooleanField(default=False)
    sala = models.ForeignKey(
        Sala,
        on_delete=models.PROTECT,
        related_name="tareas",
        null=True,
        blank=True,
    )
    def __str__(self):
        return f"{self.titulo} ({self.materia.nombre})"

class RegistroEstudio(models.Model):
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name="registros_estudio",
    )
    sala = models.ForeignKey(Sala, on_delete=models.PROTECT, null=True, blank=True, related_name="registros_estudio")
    fecha = models.DateField()
    minutos = models.PositiveIntegerField()

    class Meta:
        ordering = ["-fecha"]
        indexes = [models.Index(fields=["sala", "fecha"], name="estudio_curso_fecha_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["estudiante", "fecha", "sala"],
                condition=models.Q(sala__isnull=False),
                name="estudio_unico_dia_curso",
            ),
            models.UniqueConstraint(
                fields=["estudiante", "fecha"],
                condition=models.Q(sala__isnull=True),
                name="estudio_unico_dia_general",
            ),
            models.CheckConstraint(
                condition=models.Q(minutos__lte=1440),
                name="estudio_maximo_diario",
            ),
        ]

    def __str__(self):
        return f"{self.estudiante.nombre}: {self.minutos} min ({self.fecha})"

class Inscripcion(models.Model):
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name="inscripciones",
    )
    sala = models.ForeignKey(
        Sala,
        on_delete=models.CASCADE,
        related_name="inscripciones",
    )
    fecha_inscripcion = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["estudiante", "sala"],
                name="inscripcion_unica_por_curso",
            ),
        ]

    def __str__(self):
        return (
            f"{self.estudiante.nombre} — "
            f"{self.sala.asignatura}"
        )