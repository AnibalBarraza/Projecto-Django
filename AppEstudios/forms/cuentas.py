"""Formularios de acceso, registro y elección de rol."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from ..models import Estudiante

ROLES = [
    ("estudiante", "Estudiante"),
    ("profesor", "Profesor"),
]


def validar_perfil(formulario, datos):
    if datos.get("rol") == "estudiante":
        if datos.get("edad") is None:
            formulario.add_error("edad", "Ingresa tu edad.")

        if not datos.get("tiempo_viaje"):
            formulario.add_error(
                "tiempo_viaje",
                "Selecciona tu tiempo de viaje.",
            )

    return datos


class IngresoForm(AuthenticationForm):
    username = forms.CharField(label="Nombre de usuario")
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
    )


class ElegirRolForm(forms.Form):
    rol = forms.ChoiceField(
        label="Tipo de cuenta",
        choices=ROLES,
    )
    edad = forms.IntegerField(
        label="Edad (solo estudiantes)",
        min_value=1,
        max_value=120,
        required=False,
    )
    tiempo_viaje = forms.ChoiceField(
        label="Tiempo de viaje (solo estudiantes)",
        choices=[("", "Seleccionar")] + Estudiante.TIEMPO_VIAJE_CHOICES,
        required=False,
    )

    def clean(self):
        return validar_perfil(self, super().clean())


class RegistroCuentaForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nombre",
        max_length=100,
    )
    last_name = forms.CharField(
        label="Apellido",
        max_length=100,
    )
    rol = forms.ChoiceField(
        label="Tipo de cuenta",
        choices=ROLES,
    )
    edad = forms.IntegerField(
        label="Edad (solo estudiantes)",
        min_value=1,
        max_value=120,
        required=False,
    )
    tiempo_viaje = forms.ChoiceField(
        label="Tiempo de viaje (solo estudiantes)",
        choices=[("", "Seleccionar")] + Estudiante.TIEMPO_VIAJE_CHOICES,
        required=False,
    )

    class Meta:
        model = get_user_model()
        fields = (
            "username",
            "first_name",
            "last_name",
            "rol",
            "edad",
            "tiempo_viaje",
            "password1",
            "password2",
        )

    def clean(self):
        return validar_perfil(self, super().clean())
