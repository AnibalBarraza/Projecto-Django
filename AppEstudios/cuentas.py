from django.contrib.auth.models import Group
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Estudiante, Inscripcion, Sala
from .acceso import es_profesor, perfil, profesor_request
from .forms import IngresoForm, ElegirRolForm, RegistroCuentaForm


class IngresarView(LoginView):
    template_name = "cuenta.html"
    authentication_form = IngresoForm
    extra_context = {"modo": "ingreso"}
    redirect_authenticated_user = False

    def get_success_url(self):
        return "/mi-cuenta/"


class CambiarCuentaView(IngresarView):
    """Authenticate another identity before replacing the current session."""

    extra_context = {"modo": "ingreso", "cambio_cuenta": True}


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


def registrarse(request):
    rol_inicial = request.GET.get("rol", "estudiante")
    if rol_inicial not in ("estudiante", "profesor"):
        rol_inicial = "estudiante"
    formulario = RegistroCuentaForm(request.POST or None, initial={"rol": rol_inicial})

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
    if (
        profesor_request(request)
        or Estudiante.objects.filter(usuario=request.user).exists()
    ):
        return redirect("tablero")

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
        usuario = get_user_model().objects.select_for_update().get(pk=request.user.pk)

        if es_profesor(usuario) or Estudiante.objects.filter(usuario=usuario).exists():
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
    estudiante = perfil(request)

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
        return redirect("tablero")

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
        "Inscripción completada." if nueva else "Ya estás inscrito en este curso.",
    )
    return redirect("tablero")
