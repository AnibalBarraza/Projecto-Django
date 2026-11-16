"""Registro diario de estudio y meta global."""

from django import forms
from django.utils import timezone
from ..models import Sala


class RegistroEstudioForm(forms.Form):
    sala = forms.ModelChoiceField(
        queryset=Sala.objects.none(),
        required=False,
        empty_label="Estudio general",
        label="Curso",
    )
    fecha = forms.DateField(
        label="Fecha", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    )
    minutos = forms.IntegerField(
        label="Total diario de minutos para este curso", min_value=0, max_value=1440
    )
    meta_semanal_minutos = forms.IntegerField(
        label="Meta semanal global (minutos)", min_value=1, max_value=10080
    )

    def __init__(self, *args, estudiante=None, **kwargs):
        super().__init__(*args, **kwargs)
        if estudiante is not None:
            self.fields["sala"].queryset = estudiante.cursos.all()

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError(
                "No puedes registrar estudio en una fecha futura."
            )
        return fecha
