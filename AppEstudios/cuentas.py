from functools import wraps

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


class RegistroCuentaForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", max_length=100)
    last_name = forms.CharField(label="Apellido", max_length=100)

    edad = forms.IntegerField(
        label="Edad",
        min_value=1,
        max_value=120,
    )

    tiempo_viaje = forms.ChoiceField(
        label="Tiempo de viaje",
        choices=Estudiante.TIEMPO_VIAJE_CHOICES,
    )

    tengo_registros = forms.BooleanField(
        required=False,
        label=(
            "Ya tengo notas o registros anteriores: "
            "solicitar vinculación de mi cuenta"
        ),
    )

    class Meta:
        model = get_user_model()
        fields = (
            "username",
            "first_name",
            "last_name",
            "edad",
            "tiempo_viaje",
            "tengo_registros",
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

            if not formulario.cleaned_data["tengo_registros"]:
                Estudiante.objects.create(
                    usuario=usuario,
                    nombre=usuario.first_name,
                    apellido=usuario.last_name,
                    edad=formulario.cleaned_data["edad"],
                    tiempo_viaje=formulario.cleaned_data["tiempo_viaje"],
                )

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
        {"modo": "pendiente"},
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