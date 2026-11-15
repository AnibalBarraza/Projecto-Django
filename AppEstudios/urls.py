from django.urls import path
from . import views
from .seguimiento import guardar_estudio

urlpatterns = [
    path('', views.index, name="index"),
    path('administrador/', views.administrador, name="administrador"),
    path('cambiar-sala/<int:sala_id>/', views.cambiar_sala, name="cambiar_sala"),
    path('usuario/', views.usuario, name="usuario"),
    path('logout-usuario/', views.logout_usuario, name="logout_usuario"),
    path("guardar-estudio/", guardar_estudio, name="guardar_estudio"),
]