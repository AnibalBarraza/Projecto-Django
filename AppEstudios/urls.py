from django.urls import path, include
from . import views
urlpatterns = [
    path('',views.index,name="index"),
    path('administrador/',views.administrador,name="administrador"),
    path('usuario/',views.usuario,name="usuario")
]
