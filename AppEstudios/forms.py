from django import forms
from django.utils import timezone


class RegistroEstudioForm(forms.Form):
    fecha = forms.DateField(
        label="Fecha",
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control"},
            format="%Y-%m-%d",
        ),
    )
    minutos = forms.IntegerField(
        label="Total de minutos estudiados ese día",
        min_value=0,
        max_value=1440,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    meta_semanal_minutos = forms.IntegerField(
        label="Mi meta semanal en minutos",
        min_value=1,
        max_value=10080,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError(
                "No puedes registrar estudio en una fecha futura."
            )
        return fecha