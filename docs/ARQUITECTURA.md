# Estructura del proyecto

Las rutas públicas no cambiaron. `AppEstudios/urls.py` conecta cada URL con las entradas de `views.py`; este archivo solo expone las vistas implementadas por área en `vistas/`.

## Dónde hacer cada cambio

| Responsabilidad | Ubicación |
| --- | --- |
| Inicio de sesión, registro, elección de rol e inscripción | `AppEstudios/cuentas.py` |
| Comprobación de roles y cursos visibles por petición | `AppEstudios/acceso.py` |
| Vistas del tablero, cursos, rendimiento, calendario y estudio | `AppEstudios/vistas/` |
| Formularios de cuentas, cursos y estudio | `AppEstudios/forms/` |
| Consultas, filtros, agregados y datos de las pantallas | `AppEstudios/consultas/` |
| Guardado de cursos, notas, tareas y estudio; cierre de semestre | `AppEstudios/servicios.py` |
| Selección de semestre/año y paginación compartida | `AppEstudios/periodos.py`, `AppEstudios/paginacion.py` |
| Colores y navegación compartidos | `AppEstudios/presentacion.py` |
| Datos de gráficos reutilizables y gráficos por área | `AppEstudios/graficos*.py` |
| Historia de estudiantes para la exploración y enlaces de retorno | `AppEstudios/consultas/exploracion.py`, `AppEstudios/exploracion.py` |
| Pantallas y componentes HTML activos | `AppEstudios/templates/portal/` |
| Estilos y comportamiento de gráficos | `AppEstudios/static/AppEstudios/` |
| Pruebas separadas por área y datos compartidos | `AppEstudios/tests/` |
| Pantallas anteriores, fuera de las rutas y plantillas activas | `docs/archivo_interfaz_anterior/` |

## Límites entre responsabilidades

Las vistas comprueban el acceso, reciben formularios y devuelven respuestas HTTP. Las consultas reciben el curso y usuario ya autorizados y filtran sus datos. Los servicios reciben datos validados por los formularios y conservan las transacciones necesarias para guardar. Los módulos de gráficos trabajan con los datos consultados, sin ejecutar consultas propias.

Los roles y perfiles solo se reutilizan dentro de la misma petición. El ID de curso procede de la URL; ninguna escritura depende de un curso activo guardado en sesión. Los cambios de organización no requieren nuevas migraciones ni modifican el historial de migraciones.

## Plantillas

`portal/base.html` contiene el documento compartido y carga los archivos estáticos. `portal/curso.html` presenta el encabezado y la navegación e incluye una plantilla de la lista de secciones permitidas:

- `portal/cursos/resumen.html`
- `portal/cursos/calificaciones.html`
- `portal/cursos/estudiantes.html`
- `portal/cursos/habitos.html`
- `portal/cursos/tareas.html`
- `portal/cursos/configuracion.html`

El filtro de período y la navegación entre páginas están en `portal/componentes/`. La tabla de notas y los gráficos se reutilizan en el detalle y la ficha del estudiante.

## Paginación y cálculos

Las notas se consultan de 30 en 30. El promedio y la distribución del período se calculan mediante agregados sobre todas sus notas antes de paginar. El gráfico individual representa únicamente las notas de la página visible y cada barra tiene un destino presente en esa página.

El listado de estudiantes, los hábitos y las tareas también se paginan de 30 en 30. El gráfico de promedios de estudiantes tiene su propio parámetro `pagina_estudiantes`; la distribución sigue considerando todo el período. Los enlaces conservan semestre, año y rango seleccionado.

La exploración histórica consulta como máximo ocho períodos y agrega las notas de los estudiantes de la página visible en dos consultas, sin consultas individuales por alumno. Los períodos posteriores al seleccionado se excluyen. La matriz incluye alumnos sin notas actuales; los gráficos de promedio y de cambio solo representan los registros que requieren. La navegación por bandas usa HTML del servidor para conservar las mismas reglas de acceso, filtros y agregados; JavaScript reemplaza el contenido y mantiene el historial del navegador.

Las copias históricas de tareas por estudiante se agrupan en SQL antes de paginar el listado del profesor. Desde el calendario se abre la entrega seleccionada mediante un filtro por ID, comprobando que sea visible para la cuenta; así también funciona si la entrega no está en la primera página. Un enlace permite volver a todas las tareas del curso.

## Pruebas y formato

Las pruebas usan SQLite temporal e independiente de RDS. Los módulos cubren cuentas, cursos, calendario, rendimiento, estudio, consultas, paginación y migraciones. `tests/base.py` contiene datos y utilidades compartidos; no contiene pruebas heredadas que se ejecuten varias veces.

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=Proyecto_Estudio.test_settings
.\.venv\Scripts\python.exe scripts/verify_portal_browser.py
```

Los formateadores opcionales están en `requirements-dev.txt`; la configuración compartida está en `pyproject.toml`. Para mantener el estilo de los archivos activos:

```powershell
.\.venv\Scripts\python.exe -m black AppEstudios/vistas AppEstudios/consultas AppEstudios/forms AppEstudios/tests
.\.venv\Scripts\python.exe -m djlint AppEstudios/templates/portal --reformat
```


El criterio visual y el significado de los nuevos gráficos se documentan en [DISENO.md](DISENO.md). Las bandas de ancho uniforme del histograma se filtran con `banda`; los enlaces antiguos con `rango` siguen funcionando. Los filtros de edad y viaje se aplican únicamente al listado autorizado del curso. El mapa de calor reutiliza una consulta de estudio acotada a las últimas cuatro semanas para preparar también los totales semanales.


## Inicio y cambio de cuenta

`vistas/inicio.py` presenta la página pública sin consultar datos académicos. `templates/publica/base.html` comparte encabezado y pie de inicio y cuentas; `static/AppEstudios/inicio.css` contiene sus estilos. `/crear-curso/` utiliza el mismo servicio que el formulario emergente del tablero.

`cuentas.CambiarCuentaView` utiliza la autenticación de Django para validar otra cuenta antes de reemplazar la sesión. El ingreso sigue siendo accesible si ya hay un usuario autenticado; un intento fallido no cierra su sesión. `acceso.profesor_request` depende exclusivamente del rol real y `acceso.perfil` rechaza el uso de herramientas de estudiante con una cuenta de profesor. No se crean perfiles ni se reasignan cursos al cambiar de cuenta.

Las cuentas de profesor y estudiante se prueban con identidades distintas. Ya no hay selector de roles de prueba, endpoint `cambiar-vista` ni configuración que autorice a cambiar el rol mediante la sesión.
