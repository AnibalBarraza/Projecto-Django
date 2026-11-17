# Criterio visual y gráficos

El rediseño toma como referencia los mockups de las páginas 6 a 8 de la presentación del proyecto: menú lateral claro, tarjetas compactas, indicadores de resumen y paneles visuales agrupados. La presentación se usa como referencia de diseño y contexto; sus afirmaciones no se convierten en reglas de predicción de la aplicación.

## Calificaciones

La pantalla sigue este orden:

1. Curso, sección y período seleccionado.
2. Promedio, cantidad de notas y cobertura del curso o rango de notas individual.
3. Acción plegable para registrar una nota, indicando su curso y período actual.
4. Gráficos relacionados, en una cuadrícula de dos columnas en escritorio.
5. Registro individual: plegado en el curso del profesor, visible en la ficha y en la cuenta del estudiante.

Los indicadores del profesor consideran el curso completo y así se rotulan, aunque se seleccione una banda del histograma. El filtro afecta al listado de notas y los puntos de estudiantes; se puede quitar sin perder semestre y año. La banda elegida se resalta en el histograma.

## Cada gráfico responde una pregunta

| Gráfico | Qué representa | Al seleccionar |
| --- | --- | --- |
| Histograma de promedios | Cantidad de estudiantes por intervalo de un punto: 1–<2, 2–<3, …, 6–7 | Filtra estudiantes y notas de esa banda |
| Puntos por estudiante | Promedio individual del curso y período | Abre su ficha |
| Puntos de notas | Cada calificación, por orden de registro | Abre el detalle de la nota |
| Línea por semestre | Promedios de períodos con notas, diferenciando año y semestre | Consulta el período seleccionado; en una ficha conserva al estudiante |
| Mapa de promedios por semestre | Estudiantes de la página actual × últimos ocho períodos hasta el seleccionado | Abre la ficha en ese semestre y conserva el contexto de origen |
| Promedio y cantidad de notas | Promedio individual frente a la cantidad de calificaciones del período | Abre las notas del estudiante; la tabla alternativa permite distinguir puntos superpuestos |
| Cambio entre semestres | Diferencia de promedio respecto al período anterior del curso con notas | Abre la ficha con comparación de ambos promedios y cantidad de notas |
| Columnas de edades | Cantidad de inscritos por edad | Lista esos estudiantes del curso |
| Barras de tiempo de viaje | Cantidad de inscritos por tramo de viaje | Lista esos estudiantes del curso |
| Columnas de estudio diario | Minutos registrados cada día de esta semana | Abre el historial de ese día |
| Anillo de estudio | Reparto de los minutos semanales entre cursos y estudio general | Abre las calificaciones del curso; Estudio general abre Rendimiento general |
| Mapa de calor de estudio | Minutos diarios de las últimas cuatro semanas | Abre los registros de la fecha seleccionada |

El anillo aparece cuando hay más de una categoría y minutos positivos. No se usa un gráfico circular para comparar promedios. Los puntos de notas no se unen: el modelo no incluye fechas de evaluación que permitan afirmar una evolución cronológica dentro del semestre. La referencia visual 4,0 no representa una predicción de reprobación.

El mapa muestra «—» para períodos sin notas: no equivale a cero. La comparación solo incluye estudiantes con notas en ambos períodos y usa una escala de −6 a +6 puntos. Si no hay un período anterior, se explica qué datos faltan. Los nuevos gráficos comparten el rango y la paginación de estudiantes; el histograma y los indicadores mantienen los totales del curso completo.

Seleccionar una banda o quitar el filtro actualiza el contenido con JavaScript sin recargar el documento. La selección queda indicada y se lleva allí el foco; Atrás y Adelante recuperan el estado. Los enlaces siguen funcionando sin JavaScript. La ficha conserva semestre, año, rango y página de origen en un retorno restringido a filtros locales, también al recorrer el historial o aplicar otro período.

En el resumen, edades y tiempos de viaje quedan dentro de «Contexto del curso», plegado inicialmente, para dar prioridad a los datos académicos.

Las líneas históricas requieren al menos dos períodos con notas. No se inventan registros para completar períodos ausentes. El estudio no se cruza con notas de toda la historia; edad y viaje describen el curso sin atribuirles causalidad. No se muestran asistencia, consumo de alcohol ni otras variables que no se registran en la aplicación.

## Acceso y verificación

Todas las marcas son enlaces utilizables con teclado. Hay tablas alternativas de datos, valores al enfocar y enlaces para volver al contexto anterior. Las tablas y gráficos conservan la paginación; las cifras del período completo se calculan antes de paginar.

Los recorridos se verifican con una base temporal: histogramas, fichas, notas, teclado, filtros de perfiles, segmentos del anillo y celdas del mapa de calor. También se comprueba el diseño móvil y la ausencia de errores de JavaScript. Las capturas generadas por `scripts/verify_portal_browser.py` contienen exclusivamente datos ficticios de prueba.
