from django.shortcuts import render

def index(request):
    return render(request,"index.html")

def administrador(request):
    return render(request,"administrador.html")

def usuario(request):
    return render(request,"usuario.html")
