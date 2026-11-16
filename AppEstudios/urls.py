from django.urls import path
from . import cuentas, views

urlpatterns = [
    path("", views.inicio, name="index"),
    path("crear-curso/", views.crear_curso, name="crear_curso"),
    path("cambiar-cuenta/", cuentas.CambiarCuentaView.as_view(), name="cambiar_cuenta"),
    path("tablero/", views.tablero, name="tablero"),
    path("administrador/", views.tablero, name="administrador"),
    path("usuario/", views.tablero, name="usuario"),
    path("cursos/<int:curso_id>/", views.curso, name="curso"),
    path(
        "cursos/<int:curso_id>/estudiantes/<int:estudiante_id>/",
        views.curso,
        {"seccion": "estudiantes"},
        name="ficha_estudiante",
    ),
    path("cursos/<int:curso_id>/<str:seccion>/", views.curso, name="curso_seccion"),
    path("rendimiento/", views.rendimiento, name="rendimiento"),
    path("calendario/", views.calendario, name="calendario"),
    path("estudio/", views.estudio, name="estudio"),
    path("guardar-estudio/", views.estudio, name="guardar_estudio"),
    path("ingresar/", cuentas.IngresarView.as_view(), name="ingresar"),
    path("elegir-rol/", cuentas.elegir_rol, name="elegir_rol"),
    path("registrarse/", cuentas.registrarse, name="registrarse"),
    path("mi-cuenta/", cuentas.mi_cuenta, name="mi_cuenta"),
    path("salir/", cuentas.salir, name="salir"),
    path("logout-usuario/", cuentas.salir, name="logout_usuario"),
    path("inscribirse/", cuentas.inscribirse, name="inscribirse"),
]
