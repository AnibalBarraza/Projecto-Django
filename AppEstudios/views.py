from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Avg, Count
from .models import Sala, Estudiante, Materia, Calificacion, Tarea

def index(request):
    return render(request, "index.html")

def administrador(request):
    if request.method == 'POST':
        # 1. Crear Sala
        if 'crear_sala' in request.POST:
            profesor = request.POST.get('nombre_profesor', '').strip()
            asignatura = request.POST.get('asignatura', '').strip()
            if profesor and asignatura:
                nueva_sala = Sala.objects.create(nombre_profesor=profesor, asignatura=asignatura)
                request.session['sala_activa_id'] = nueva_sala.id
                return redirect('administrador')

        # 2. Agregar Estudiante
        elif 'crear_estudiante' in request.POST:
            sala_id = request.session.get('sala_activa_id')
            sala_activa = Sala.objects.filter(id=sala_id).first()
            if sala_activa:
                nombre = request.POST.get('nombre', '').strip()
                edad = request.POST.get('edad', 15)
                tiempo_viaje = request.POST.get('tiempo_viaje', '< 15 min')
                if nombre:
                    Estudiante.objects.create(
                        nombre=nombre,
                        edad=int(edad),
                        tiempo_viaje=tiempo_viaje,
                        sala=sala_activa
                    )
            return redirect('administrador')

        # 3. Registrar Calificación
        elif 'crear_nota' in request.POST:
            estudiante_id = request.POST.get('estudiante_id')
            materia_nombre = request.POST.get('materia_nombre', '').strip()
            semestre = request.POST.get('semestre', 1)
            nota = request.POST.get('nota', 7.0)

            estudiante = Estudiante.objects.filter(id=estudiante_id).first()
            if estudiante and materia_nombre:
                materia, _ = Materia.objects.get_or_create(nombre=materia_nombre)
                Calificacion.objects.create(
                    estudiante=estudiante,
                    materia=materia,
                    semestre=int(semestre),
                    nota=float(nota)
                )
            return redirect('administrador')

        # 4. Asignar Tarea
        elif 'crear_tarea' in request.POST:
            estudiante_id = request.POST.get('estudiante_id')
            materia_nombre = request.POST.get('materia_nombre', '').strip()
            titulo = request.POST.get('titulo', '').strip()
            fecha_entrega = request.POST.get('fecha_entrega')

            estudiante = Estudiante.objects.filter(id=estudiante_id).first()
            if estudiante and materia_nombre and titulo and fecha_entrega:
                materia, _ = Materia.objects.get_or_create(nombre=materia_nombre)
                Tarea.objects.create(
                    estudiante=estudiante,
                    materia=materia,
                    titulo=titulo,
                    fecha_entrega=fecha_entrega,
                    completada=False
                )
            return redirect('administrador')

    todas_las_salas = Sala.objects.all()
    sala_id = request.session.get('sala_activa_id')
    sala_activa = Sala.objects.filter(id=sala_id).first() if sala_id else todas_las_salas.first()

    if not sala_activa:
        return render(request, "administrador.html", {'sin_salas': True, 'todas_las_salas': []})

    request.session['sala_activa_id'] = sala_activa.id

    estudiantes_sala = Estudiante.objects.filter(sala=sala_activa)
    todas_las_materias = Materia.objects.all()

    total_estudiantes = estudiantes_sala.count()
    promedio_general = Calificacion.objects.filter(estudiante__in=estudiantes_sala).aggregate(Avg('nota'))['nota__avg'] or 0.0
    tareas_pendientes = Tarea.objects.filter(estudiante__in=estudiantes_sala, completada=False).count()

    edades_query = estudiantes_sala.values('edad').annotate(total=Count('id')).order_by('edad')
    g1_labels = [f"{item['edad']} años" for item in edades_query]
    g1_data = [item['total'] for item in edades_query]

    viaje_query = estudiantes_sala.values('tiempo_viaje').annotate(total=Count('id'))
    g2_labels = [item['tiempo_viaje'] for item in viaje_query]
    g2_data = [item['total'] for item in viaje_query]

    semestres_query = Calificacion.objects.filter(estudiante__in=estudiantes_sala).values('semestre').annotate(prom=Avg('nota')).order_by('semestre')
    g3_labels = [f"Semestre {item['semestre']}" for item in semestres_query]
    g3_data = [round(item['prom'], 1) for item in semestres_query]

    materias_query = Calificacion.objects.filter(estudiante__in=estudiantes_sala).values('materia__nombre').annotate(prom=Avg('nota'))
    g4_labels = [item['materia__nombre'] for item in materias_query]
    g4_data = [round(item['prom'], 1) for item in materias_query]

    context = {
        'sin_salas': False,
        'sala_activa': sala_activa,
        'todas_las_salas': todas_las_salas,
        'todas_las_materias': todas_las_materias,
        'kpi_total_estudiantes': total_estudiantes,
        'kpi_promedio_general': round(promedio_general, 1),
        'kpi_tareas_pendientes': tareas_pendientes,
        'g1_labels': g1_labels,
        'g1_data': g1_data,
        'g2_labels': g2_labels,
        'g2_data': g2_data,
        'g3_labels': g3_labels,
        'g3_data': g3_data,
        'g4_labels': g4_labels,
        'g4_data': g4_data,
        'estudiantes': estudiantes_sala,
    }
    return render(request, "administrador.html", context)

def cambiar_sala(request, sala_id):
    request.session['sala_activa_id'] = sala_id
    return redirect('administrador')

def usuario(request):
    if request.method == 'POST':
        nombre_ingresado = request.POST.get('nombre_estudiante', '').strip()
        codigo_ingresado = request.POST.get('codigo_sala', '').strip().upper()

        sala_encontrada = Sala.objects.filter(codigo=codigo_ingresado).first()

        if not sala_encontrada:
            return render(request, "usuario.html", {
                'mostrar_login': True,
                'error_login': f"El código de sala '{codigo_ingresado}' no existe."
            })

        estudiante = Estudiante.objects.filter(nombre__iexact=nombre_ingresado, sala=sala_encontrada).first()

        if not estudiante:
            estudiante_sin_sala = Estudiante.objects.filter(nombre__iexact=nombre_ingresado).first()
            if estudiante_sin_sala:
                estudiante = estudiante_sin_sala
                estudiante.sala = sala_encontrada
                estudiante.save()
            else:
                estudiante = Estudiante.objects.create(
                    nombre=nombre_ingresado,
                    edad=15,
                    tiempo_viaje='< 15 min',
                    sala=sala_encontrada
                )

        request.session['estudiante_id'] = estudiante.id
        return redirect('usuario')

    estudiante_id = request.session.get('estudiante_id')
    if not estudiante_id:
        return render(request, "usuario.html", {'mostrar_login': True})

    estudiante = Estudiante.objects.filter(id=estudiante_id).first()
    if not estudiante:
        request.session.flush()
        return redirect('usuario')

    promedio_estudiante = Calificacion.objects.filter(estudiante=estudiante).aggregate(Avg('nota'))['nota__avg'] or 0.0
    materias_inscritas = Calificacion.objects.filter(estudiante=estudiante).values('materia').distinct().count()
    tareas_pendientes = Tarea.objects.filter(estudiante=estudiante, completada=False).count()

    notas_materia = Calificacion.objects.filter(estudiante=estudiante).values('materia__nombre').annotate(prom=Avg('nota'))
    g1_labels = [item['materia__nombre'] for item in notas_materia]
    g1_data = [round(item['prom'], 1) for item in notas_materia]

    notas_semestre = Calificacion.objects.filter(estudiante=estudiante).values('semestre').annotate(prom=Avg('nota')).order_by('semestre')
    g2_labels = [f"Semestre {item['semestre']}" for item in notas_semestre]
    g2_data = [round(item['prom'], 1) for item in notas_semestre]

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
    request.session.flush()
    return redirect('usuario')