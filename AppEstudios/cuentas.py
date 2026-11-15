from functools import wraps
from django.contrib.auth.models import Group
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Estudiante, Inscripcion, Sala


def es_profesor(usuario):
    return usuario.is_authenticated and (
        usuario.is_superuser
        or usuario.groups.filter(name="Profesores").exists()
    )


def salas_del_profesor(usuario):
    if not es_profesor(usuario):
        raise PermissionDenied("Esta sección es para profesores.")

    if usuario.is_superuser:
        return Sala.objects.all()

    return Sala.objects.filter(profesor=usuario)


def acceso_profesor(vista):
    @login_required(login_url="ingresar")
    @wraps(vista)
    def protegida(request, *args, **kwargs):
        salas_del_profesor(request.user)
        return vista(request, *args, **kwargs)

    return protegida


class IngresoForm(AuthenticationForm):
    username = forms.CharField(label="Nombre de usuario")
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
    )


class IngresarView(LoginView):
    template_name = "cuenta.html"
    authentication_form = IngresoForm
    extra_context = {"modo": "ingreso"}
    redirect_authenticated_user = True

    def get_success_url(self):
        return "/mi-cuenta/"

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


def crear_perfil(usuario, datos):
    if datos["rol"] == "profesor":
        grupo, _ = Group.objects.get_or_create(name="Profesores")
        usuario.groups.add(grupo)
    else:
        Estudiante.objects.create(
            usuario=usuario,
            nombre=usuario.first_name or usuario.username,
            apellido=usuario.last_name,
            edad=datos["edad"],
            tiempo_viaje=datos["tiempo_viaje"],
        )

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


def registrarse(request):
    if request.user.is_authenticated:
        return redirect("mi_cuenta")

    formulario = RegistroCuentaForm(request.POST or None)

    if request.method == "POST" and formulario.is_valid():
        with transaction.atomic():
            usuario = formulario.save()
            crear_perfil(usuario, formulario.cleaned_data)

        login(request, usuario)
        return redirect("mi_cuenta")

    return render(
        request,
        "cuenta.html",
        {"form": formulario, "modo": "registro"},
    )

@login_required(login_url="ingresar")
def mi_cuenta(request):
    if es_profesor(request.user):
        return redirect("administrador")

    if Estudiante.objects.filter(usuario=request.user).exists():
        return redirect("usuario")

    return render(
        request,
        "cuenta.html",
        {
            "modo": "pendiente",
            "form": ElegirRolForm(),
        },
    )

@login_required(login_url="ingresar")
@require_POST
def elegir_rol(request):
    with transaction.atomic():
        usuario = (
            get_user_model().objects
            .select_for_update()
            .get(pk=request.user.pk)
        )

        if (
            es_profesor(usuario)
            or Estudiante.objects.filter(usuario=usuario).exists()
        ):
            return redirect("mi_cuenta")

        formulario = ElegirRolForm(request.POST)

        if formulario.is_valid():
            crear_perfil(usuario, formulario.cleaned_data)
            return redirect("mi_cuenta")

    return render(
        request,
        "cuenta.html",
        {
            "modo": "pendiente",
            "form": formulario,
        },
    )

@login_required(login_url="ingresar")
@require_POST
def salir(request):
    logout(request)
    return redirect("ingresar")


@login_required(login_url="ingresar")
@require_POST
def inscribirse(request):
    estudiante = get_object_or_404(
        Estudiante,
        usuario=request.user,
    )

    codigo = request.POST.get("codigo_sala", "").strip().upper()

    sala = Sala.objects.filter(
        codigo=codigo,
        archivada=False,
    ).first()

    if sala is None:
        messages.error(
            request,
            "No encontramos un curso activo con ese código.",
        )
        return redirect("usuario")

    _, nueva = Inscripcion.objects.get_or_create(
        estudiante=estudiante,
        sala=sala,
    )

    # Compatibilidad con la pantalla actual.
    if estudiante.sala_id is None:
        estudiante.sala = sala
        estudiante.save(update_fields=["sala"])

    messages.success(
        request,
        "Inscripción completada."
        if nueva else "Ya estás inscrito en este curso.",
    )
    return redirect("usuario")