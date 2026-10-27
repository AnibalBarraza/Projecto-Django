from django.shortcuts import render,redirect
from django.db.models import Avg, Count
from .models import Estudiante, Materia, Calificacion, Tarea

def index(request):
    return render(request, "index.html")

def administrador(request):
    # 1. CÁLCULO DE KPIs PARA EL ADMINISTRADOR (Exigencia de la rúbrica: mín 3)
    total_estudiantes = Estudiante.objects.count()
    promedio_general = Calificacion.objects.aggregate(Avg('nota'))['nota__avg'] or 0.0
    tareas_pendientes = Tarea.objects.filter(completada=False).count()

    # 2. DATOS PARA LOS 4 GRÁFICOS DEL ADMINISTRADOR (Exigencia de la rúbrica: mín 4)
    
    # Gráfico 1: Personas por Edad
    edades_query = Estudiante.objects.values('edad').annotate(total=Count('id')).order_by('edad')
    grafico_edades_labels = [str(item['edad']) + ' años' for item in edades_query]
    grafico_edades_data = [item['total'] for item in edades_query]

    # Gráfico 2: Tiempo de Viaje
    viaje_query = Estudiante.objects.values('tiempo_viaje').annotate(total=Count('id'))
    grafico_viaje_labels = [item['tiempo_viaje'] for item in viaje_query]
    grafico_viaje_data = [item['total'] for item in viaje_query]

    # Gráfico 3: Promedio por Semestre
    semestres_query = Calificacion.objects.values('semestre').annotate(prom=Avg('nota')).order_by('semestre')
    grafico_semestre_labels = [f"Semestre {item['semestre']}" for item in semestres_query]
    grafico_semestre_data = [round(item['prom'], 1) for item in semestres_query]

    # Gráfico 4: Promedio por Materia
    materias_query = Calificacion.objects.values('materia__nombre').annotate(prom=Avg('nota'))
    grafico_materia_labels = [item['materia__nombre'] for item in materias_query]
    grafico_materia_data = [round(item['prom'], 1) for item in materias_query]

    # 3. LISTADO PARA LA TABLA HTML (Exigencia de la rúbrica)
    lista_estudiantes = Estudiante.objects.all()

    context = {
        'kpi_total_estudiantes': total_estudiantes,
        'kpi_promedio_general': round(promedio_general, 1),
        'kpi_tareas_pendientes': tareas_pendientes,
        'g1_labels': grafico_edades_labels,
        'g1_data': grafico_edades_data,
        'g2_labels': grafico_viaje_labels,
        'g2_data': grafico_viaje_data,
        'g3_labels': grafico_semestre_labels,
        'g3_data': grafico_semestre_data,
        'g4_labels': grafico_materia_labels,
        'g4_data': grafico_materia_data,
        'estudiantes': lista_estudiantes,
    }
    return render(request, "administrador.html", context)

def usuario(request):
    # 1. SI VIENE UN FORMULARIO CON EL NOMBRE (Proceso de Login)
    if request.method == 'POST':
        nombre_ingresado = request.POST.get('nombre_estudiante', '').strip()
        # Buscamos al estudiante por nombre (sin importar mayúsculas/minúsculas)
        estudiante_encontrado = Estudiante.objects.filter(nombre__iexact=nombre_ingresado).first()
        
        if estudiante_encontrado:
            # Guardamos el ID en la memoria de la sesión
            request.session['estudiante_id'] = estudiante_encontrado.id
            return redirect('usuario')
        else:
            # Si no existe el estudiante, devolvemos un mensaje de error
            todos = Estudiante.objects.all()
            return render(request, "usuario.html", {
                'mostrar_login': True,
                'error_login': f"No se encontró ningún estudiante llamado '{nombre_ingresado}'.",
                'lista_estudiantes': todos
            })

    # 2. VERIFICAR SI YA HAY UN ESTUDIANTE EN SESIÓN
    estudiante_id = request.session.get('estudiante_id')
    
    # Si no hay sesión iniciada, mostramos la pantalla de Login
    if not estudiante_id:
        todos = Estudiante.objects.all()
        return render(request, "usuario.html", {
            'mostrar_login': True,
            'lista_estudiantes': todos
        })

    # 3. SI HAY SESIÓN, CARGAMOS AL ESTUDIANTE Y SUS DATOS
    estudiante = Estudiante.objects.filter(id=estudiante_id).first()
    
    # Si por alguna razón el estudiante fue borrado de la BD
    if not estudiante:
        request.session.flush()
        return redirect('usuario')

    # KPIs del Estudiante
    promedio_estudiante = Calificacion.objects.filter(estudiante=estudiante).aggregate(Avg('nota'))['nota__avg'] or 0.0
    materias_inscritas = Calificacion.objects.filter(estudiante=estudiante).values('materia').distinct().count()
    tareas_pendientes = Tarea.objects.filter(estudiante=estudiante, completada=False).count()

    # Gráficos del Estudiante
    notas_materia = Calificacion.objects.filter(estudiante=estudiante).values('materia__nombre').annotate(prom=Avg('nota'))
    g1_labels = [item['materia__nombre'] for item in notas_materia]
    g1_data = [round(item['prom'], 1) for item in notas_materia]

    notas_semestre = Calificacion.objects.filter(estudiante=estudiante).values('semestre').annotate(prom=Avg('nota')).order_by('semestre')
    g2_labels = [f"Trimestre {item['semestre']}" for item in notas_semestre]
    g2_data = [round(item['prom'], 1) for item in notas_semestre]

    # Lista de Tareas
    tareas_lista = Tarea.objects.filter(estudiante=estudiante, completada=False)[:5]

    context = {
        'mostrar_login': False,
        'estudiante': estudiante,
        'kpi_promedio': round(promedio_estudiante, 1),
        'kpi_materias': materias_inscritas,
        'kpi_tareas': tareas_pendientes,
        'g1_labels': g1_labels,
        'g1_data': g1_data,
        'g2_labels': g2_labels,
        'g2_data': g2_data,
        'tareas': tareas_lista,
    }
    return render(request, "usuario.html", context)

def logout_usuario(request):
    # Limpia la memoria de sesión y vuelve a pedir el nombre
    request.session.flush()
    return redirect('usuario')
