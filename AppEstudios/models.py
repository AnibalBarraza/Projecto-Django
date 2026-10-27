import uuid
from django.db import models

class Sala(models.Model):
    nombre_profesor = models.CharField(max_length=100)
    asignatura = models.CharField(max_length=100)
    codigo = models.CharField(max_length=10, unique=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = uuid.uuid4().hex[:6].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asignatura} - Prof. {self.nombre_profesor} (Código: {self.codigo})"

class Estudiante(models.Model):
    nombre = models.CharField(max_length=100)
    edad = models.IntegerField()
    
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
    nota = models.FloatField()

    def __str__(self):
        return f"{self.estudiante.nombre} - {self.materia.nombre}: {self.nota}"

class Tarea(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    fecha_entrega = models.DateField()
    completada = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.titulo} ({self.materia.nombre})"