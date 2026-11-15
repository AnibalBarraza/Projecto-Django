from django.urls import path
from . import views, cuentas
from .seguimiento import guardar_estudio

urlpatterns = [
    path('', views.index, name="index"),
    path('administrador/', views.administrador, name="administrador"),
    path('cambiar-sala/<int:sala_id>/', views.cambiar_sala, name="cambiar_sala"),
    path('usuario/', views.usuario, name="usuario"),
    path('logout-usuario/', views.logout_usuario, name="logout_usuario"),
    path("guardar-estudio/", guardar_estudio, name="guardar_estudio"),
        path(
        "ingresar/",
        cuentas.IngresarView.as_view(),
        name="ingresar",
    ),
    path("registrarse/", cuentas.registrarse, name="registrarse"),
    path("mi-cuenta/", cuentas.mi_cuenta, name="mi_cuenta"),
    path("salir/", cuentas.salir, name="salir"),
    path("inscribirse/", cuentas.inscribirse, name="inscribirse"),
]