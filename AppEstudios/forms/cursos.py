from django import forms
from ..models import Sala, Estudiante


class CursoForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ["asignatura", "seccion", "semestre_actual", "anio_actual"]
        labels = {
            "asignatura": "Asignatura",
            "seccion": "Sección",
            "semestre_actual": "Semestre inicial",
            "anio_actual": "Año inicial",
        }

    def clean_semestre_actual(self):
        valor = self.cleaned_data["semestre_actual"]
        if valor not in (1, 2):
            raise forms.ValidationError("Selecciona semestre 1 o 2.")
        return valor

    def clean_anio_actual(self):
        valor = self.cleaned_data["anio_actual"]
        if not 1900 <= valor <= 2200:
            raise forms.ValidationError("Ingresa un año entre 1900 y 2200.")
        return valor


class EstudianteChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, estudiante):
        # Evita consultar la sala histórica desde Estudiante.__str__ por cada opción.
        return f"{estudiante.nombre} {estudiante.apellido}"


class NotaForm(forms.Form):
    estudiante = EstudianteChoiceField(
        queryset=Estudiante.objects.none(), label="Estudiante"
    )
    nota = forms.DecimalField(
        min_value=1,
        max_value=7,
        decimal_places=2,
        label="Nota (1,0 a 7,0)",
        localize=True,
    )

    def __init__(self, *args, curso, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estudiante"].queryset = curso.alumnos_inscritos.order_by(
            "apellido", "nombre"
        )


class TareaForm(forms.Form):
    titulo = forms.CharField(max_length=200, label="Título")
    fecha_entrega = forms.DateField(
        label="Fecha de entrega", widget=forms.DateInput(attrs={"type": "date"})
    )
