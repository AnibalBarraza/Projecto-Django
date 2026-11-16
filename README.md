# Plataforma de apoyo académico

Proyecto Django 6.1.1 con PostgreSQL/RDS configurado mediante `.env`. Utiliza el entorno virtual existente y las dependencias de `requirements.txt`.

## Ejecutar (PowerShell)

Desde esta carpeta (se agregó `psycopg[pool]` a las dependencias):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

`migrate` aplica las migraciones pendientes a la base configurada en tu `.env`; revísala antes de ejecutarlo. No se han aplicado migraciones a RDS durante esta implementación. La migración 0012 agrega índices por curso/período y curso/fecha, sin modificar registros. La migración 0011 conserva los registros de estudio como estudio general, permite nuevos totales diarios por curso y conserva las tareas personales existentes. No reviertas 0011 después de crear registros por curso: la restricción antigua de un registro por día podría impedirlo.

Abre http://127.0.0.1:8000/. Regístrate como Estudiante o Profesor. Elegir Profesor no otorga permisos de Django Admin. Las cuentas sin rol completan su perfil en `/mi-cuenta/`. No se vinculan personas por nombre.

## Comprobar los recorridos

1. Profesor: crea dos secciones en el tablero. Cada tarjeta muestra su código y abre un curso independiente.
2. Estudiante: inscríbete usando ambos códigos. Ambos cursos aparecen aunque no tengan notas; repetir el código no duplica la inscripción.
3. Profesor: abre ambos cursos en pestañas distintas; registra notas y tareas. Cada formulario muestra su curso y utiliza su ID en la URL. Las notas solo admiten estudiantes inscritos y valores de 1,0 a 7,0.
4. Estudiante: consulta resumen, calificaciones por semestre/año y tareas. Rendimiento general pondera por igual cada curso con notas; cada barra enlaza al detalle. Calendario permite filtrar y cambiar de mes; en móvil muestra una agenda.
5. Profesor: revisa estudiantes, ficha, distribución de promedios y hábitos de cada curso. Cierra un semestre desde Configuración escribiendo SI. Las notas anteriores siguen disponibles al seleccionar semestre y año; una pestaña desactualizada no repite el cierre.
6. Estudiante: registra estudio general y por curso en la misma fecha. Guardar otra vez actualiza el total de ese curso. La meta y progreso semanales suman todos los cursos; registra cada bloque de tiempo una sola vez.

## Pruebas aisladas (sin RDS)

```powershell
.\.venv\Scripts\python.exe manage.py check --settings=Proyecto_Estudio.test_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=Proyecto_Estudio.test_settings
.\.venv\Scripts\python.exe manage.py test --settings=Proyecto_Estudio.test_settings
```

La configuración de pruebas reemplaza la conexión por SQLite en memoria. Incluye pruebas de cuentas, permisos, aislamiento entre cursos/pestañas, períodos, promedios, calendario, estudio, CSRF y conservación de datos en la migración. La configuración normal de RDS permanece intacta. No ejecutes las pruebas con la configuración normal contra RDS.

## Alcance y límites

- Las nuevas entregas son compartidas por el curso, incluso para futuros inscritos. Las antiguas entregas individuales conservan destinatario y estado. El calendario del profesor agrupa las copias antiguas con igual curso, materia, título y fecha; dos entregas idénticas con esos datos se muestran como una sola.
- Los registros antiguos sin curso o los cursos sin profesor asociado se conservan en la base. No se reasignan por coincidencia de nombres. Requieren revisión explícita de sus relaciones para aparecer en los cursos de una cuenta.
- Los hábitos muestran únicamente minutos del curso en la semana actual. No se comparan con notas históricas: faltan fechas de evaluación para una comparación temporal válida. No se infiere causalidad ni se predicen reprobaciones.
- Los gráficos SVG interactivos se generan localmente, sin CDN: ordenación de barras, valores al enfocar, navegación con teclado, tablas de datos y enlaces equivalentes. Las líneas históricas aparecen cuando existen al menos dos períodos. Los detalles de notas también se abren con controles nativos.
- Se comprobaron las páginas con el cliente de Django y en Edge headless con vistas de escritorio y móvil. Se probaron clics, teclado, ordenación y recorridos entre niveles, sin errores de JavaScript. La migración debe validarse en una copia PostgreSQL antes de aplicarla a RDS.
- Las pantallas antiguas están archivadas en `docs/archivo_interfaz_anterior/`, fuera del directorio de plantillas de Django. Las rutas activas usan `templates/portal/`. Los accesos antiguos `/usuario/` y `/administrador/` llevan al tablero.

Para un despliegue real, configura `DJANGO_SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS`. No agregues `.env` a Git.


## Gráficos por niveles

- Rendimiento → punto de un período → promedios por curso de ese período.
- Profesor: barra de curso → histograma de promedios → intervalo → puntos de estudiantes → ficha → punto de nota → detalle. Los gráficos por estudiante se paginan sin alterar la distribución global.
- Estudiante: barra de curso → puntos de sus notas → detalle.
- Estudio: columna de día, segmento del anillo o celda del mapa de calor → historial filtrado. La meta global no cambia con el filtro. El historial se pagina de 30 en 30.
- Hábitos del profesor: barra de minutos registrados → fila del estudiante. Se mantiene la limitación temporal respecto a notas.

Semestre y año se conservan en los enlaces entre gráficos y las pestañas del curso. La distribución excluye estudiantes sin notas; ausencia de registros de estudio no se interpreta como ausencia de estudio real.

## Rendimiento y conexiones

Medición con el cliente de Django (sesión y usuario incluidos):

| Página del profesor | Antes | Después |
| --- | ---: | ---: |
| Tareas | 13 consultas | hasta 6 consultas |
| Configuración | 13 | 5 |
| Hábitos | 13 | hasta 7 |
| Rendimiento general | 9 | 5 |

La paginación agrega una consulta de conteo donde se necesita, para limitar a 30 los elementos cargados. El historial se agrupa en una sola consulta: agregar semestres no aumenta el número de consultas. Los datos de rol y perfil se reutilizan únicamente dentro de la misma petición; no se cachean permisos entre usuarios o peticiones.

La conexión PostgreSQL usa un pool compartido por los hilos de cada proceso (mínimo 1, máximo 4 conexiones), compatible con el `runserver` habitual. Las conexiones vuelven al pool al terminar cada petición y se comprueban antes de reutilizarlas. La primera petición todavía debe abrir la conexión. Si utilizas varios procesos, cada proceso tiene su propio límite.

Para desactivar el pool, configura `DB_POOL_ENABLED=false` en el entorno. En ese modo `DB_CONN_MAX_AGE` controla la persistencia de conexiones (60 segundos por defecto; no evita la creación de conexiones entre hilos nuevos de runserver). No se modificó `.env`.

Se midió únicamente conexión y `SELECT 1` en RDS, sin leer tablas ni modificar datos: abrir conexión tomó aproximadamente 2,24 s y una consulta simple tuvo mediana de 163 ms en esa muestra. Con el pool, tres consultas en hilos independientes tardaron aproximadamente 1,45 s, 323 ms y 307 ms, incluidas obtención y comprobación de conexión. Son muestras de red, no tiempos garantizados de las páginas. Menos viajes a RDS y reutilizar conexiones reducen ambas fuentes de espera.

## Verificación en navegador con datos desechables

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/verify_portal_browser.py
```

La herramienta usa SQLite en un directorio temporal y crea cuentas ficticias. No aplica migraciones ni consulta tablas en RDS. Abre Edge o Chrome instalado en modo headless; si no hay un navegador compatible, se puede instalar Chromium con `python -m playwright install chromium`. Al terminar elimina la base temporal e informa dónde guardó las capturas.


## Organización y mantenimiento

Consulta [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md) para ubicar vistas, permisos, formularios, consultas, servicios, gráficos y pruebas. Las secciones del curso tienen plantillas independientes y el CSS está en un archivo estático.

Las notas, tareas, estudiantes y hábitos muestran hasta 30 registros por página. La paginación conserva filtros y período; los promedios y la distribución se calculan sobre el período completo. Los enlaces del calendario abren la entrega seleccionada aunque no pertenezca a la primera página del listado.

Esta reorganización no agrega migraciones: conserva las migraciones 0011 y 0012 preparadas anteriormente. Se verificaron 68 pruebas y los recorridos del navegador, incluida la navegación entre páginas de notas y sus gráficos.


## Diseño basado en los mockups

La interfaz recupera el menú lateral, los indicadores compactos y los paneles visuales agrupados de la presentación del proyecto. Calificaciones separa resumen, análisis y registro; los formularios se despliegan cuando se necesitan. Estudio muestra progreso, distribución de minutos y constancia sin un formulario abierto que ocupe toda la pantalla.

[docs/DISENO.md](docs/DISENO.md) explica qué representa cada gráfico, a dónde conduce y qué límites de los datos se respetan. Hay histogramas, puntos, líneas, columnas, barras, anillos de composición y mapas de calor; cada uno utiliza los datos registrados por la aplicación. No se agregaron migraciones para este rediseño.


## Inicio público y cambio entre cuentas separadas

`/` es la página pública de presentación. `/tablero/` sigue siendo el tablero autenticado. Los enlaces de Profesor/Estudiante en el inicio preseleccionan el tipo de cuenta al registrarse.

**Cambiar de cuenta**, en la barra superior, permite ingresar con otro nombre de usuario y contraseña sin cerrar sesión previamente. Las credenciales se validan antes de reemplazar la sesión: si no son válidas, la cuenta actual permanece activa. `/ingresar/` también permite hacerlo cuando ya hay una sesión abierta.

Profesor y estudiante son cuentas independientes, cada una con su propio perfil, cursos, inscripciones y permisos. El cambio de cuenta no agrega grupos, no crea perfiles automáticamente y no permite modificar el rol por un valor de sesión. El antiguo selector de vistas fue retirado; los valores antiguos de sesión se ignoran y los datos existentes se conservan sin borrarlos ni reasignarlos.

Desde el formulario de acceso también se puede crear otra cuenta sin que la aplicación redirija automáticamente al tablero anterior. Si deseas mantener ambas abiertas al mismo tiempo, utiliza perfiles de navegador distintos o una ventana privada: las pestañas de un mismo perfil comparten la sesión de Django.

**Crear curso** está en la parte superior del tablero y abre un diálogo nativo. Se cierra con Escape o ×. El enlace también funciona sin JavaScript mediante `/crear-curso/`.

Estos cambios no agregan migraciones ni aplican cambios a RDS. Se verificaron 68 pruebas, además de los recorridos de inicio, diálogo y autenticación entre cuentas distintas en navegador de escritorio y móvil.
