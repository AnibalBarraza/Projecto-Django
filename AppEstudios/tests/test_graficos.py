"""Gráficos con significado, períodos correctos y destinos autorizados."""

from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from ..models import Inscripcion, RegistroEstudio
from .base import PortalTestCase


class GraficosTests(PortalTestCase):
    def test_histograma_cuenta_promedios_en_seis_intervalos_iguales(self):
        Inscripcion.objects.create(estudiante=self.est2, sala=self.a)
        self.nota(self.a, 1)
        self.nota(self.a, 7)  # Promedio del estudiante: 4, no dos personas.
        self.nota(self.a, 7, estudiante=self.est2)
        self.nota(self.a, 1, anio=2025)
        self.login(self.prof)
        respuesta = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2026}
        )
        histograma = respuesta.context["charts"][0]
        self.assertEqual(histograma["type"], "histograma")
        self.assertEqual([p["value"] for p in histograma["points"]], [0, 0, 0, 1, 0, 1])
        respuesta = self.client.get(histograma["points"][3]["url"])
        self.assertEqual(
            {n.estudiante_id for n in respuesta.context["notas"]}, {self.est.pk}
        )
        self.assertEqual(len(respuesta.context["notas"]), 2)
        self.assertEqual(
            respuesta.context["total_notas"], 3
        )  # Indicador del curso completo.

    def test_notas_individuales_son_puntos_sin_falsa_linea_temporal(self):
        self.nota(self.a, 3)
        self.nota(self.a, 5)
        self.login()
        respuesta = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2026}
        )
        grafico = respuesta.context["charts"][0]
        self.assertEqual(grafico["type"], "puntos")
        self.assertEqual(grafico["orientacion"], "vertical")
        self.assertIn("no representa fechas", grafico["help"])
        self.assertEqual(respuesta.context["nota_minima"], 3)
        self.assertEqual(respuesta.context["nota_maxima"], 5)

    def test_una_nota_se_muestra_como_referencia_compacta(self):
        self.nota(self.a, 5)
        self.login()
        respuesta = self.client.get(
            self.url(self.a, "calificaciones"), {"semestre": 2, "anio": 2026}
        )
        self.assertEqual(respuesta.context["charts"][0]["orientacion"], "horizontal")

    def test_historia_de_ficha_no_sale_del_estudiante(self):
        self.nota(self.a, 3, semestre=1)
        self.nota(self.a, 5)
        self.nota(self.a, 7, estudiante=self.est2)
        self.login(self.prof)
        url = reverse("ficha_estudiante", args=[self.a.pk, self.est.pk])
        respuesta = self.client.get(url, {"semestre": 2, "anio": 2026})
        historia = next(
            c for c in respuesta.context["charts"] if c["id"] == "historia-curso"
        )
        self.assertEqual([p["value"] for p in historia["points"]], [3, 5])
        for punto in historia["points"]:
            self.assertTrue(punto["url"].startswith(url))

    def test_perfil_del_curso_filtra_solo_sus_estudiantes(self):
        self.login(self.prof)
        respuesta = self.client.get(self.url(self.a, "resumen"))
        charts = {c["id"]: c for c in respuesta.context["charts"]}
        self.assertEqual(charts["edades"]["type"], "columnas")
        self.assertEqual(charts["edades"]["points"][0]["value"], 1)
        filtrada = self.client.get(charts["edades"]["points"][0]["url"])
        self.assertEqual(list(filtrada.context["alumnos"]), [self.est])
        filtrada = self.client.get(charts["viajes"]["points"][0]["url"])
        self.assertEqual(list(filtrada.context["alumnos"]), [self.est])
        self.assertEqual(
            self.client.get(self.url(self.c, "estudiantes"), {"edad": 21}).status_code,
            404,
        )

    def test_anillo_representa_minutos_no_promedios(self):
        hoy = timezone.localdate()
        for sala, minutos in [(self.a, 30), (self.b, 60), (None, 10)]:
            RegistroEstudio.objects.create(
                estudiante=self.est, sala=sala, fecha=hoy, minutos=minutos
            )
        self.login()
        respuesta = self.client.get(reverse("estudio"))
        anillo = next(
            c for c in respuesta.context["charts"] if c["id"] == "estudio-cursos"
        )
        self.assertEqual(anillo["type"], "anillo")
        self.assertEqual(anillo["unit"], "minutos")
        self.assertEqual(sum(p["value"] for p in anillo["points"]), 100)
        for punto in anillo["points"]:
            filtrada = self.client.get(reverse("estudio") + punto["url"])
            self.assertEqual(
                sum(r.minutos for r in filtrada.context["historial"]), punto["value"]
            )

    def test_mapa_de_calor_no_mezcla_usuarios_ni_inventa_dias_futuros(self):
        hoy = timezone.localdate()
        RegistroEstudio.objects.create(estudiante=self.est, fecha=hoy, minutos=25)
        RegistroEstudio.objects.create(
            estudiante=self.est, fecha=hoy - timedelta(days=40), minutos=999
        )
        RegistroEstudio.objects.create(estudiante=self.est2, fecha=hoy, minutos=888)
        self.login()
        respuesta = self.client.get(reverse("estudio"))
        calor = next(c for c in respuesta.context["charts"] if c["id"] == "constancia")
        self.assertEqual(calor["type"], "calor")
        self.assertEqual(sum(p["value"] for p in calor["points"]), 25)
        self.assertLessEqual(len(calor["points"]), 28)
        self.assertEqual(calor["points"][-1]["label"], hoy.strftime("%d/%m/%Y"))
        self.assertEqual(respuesta.context["minutos_semana"], 25)
        filtrada = self.client.get(reverse("estudio") + calor["points"][-1]["url"])
        self.assertEqual([r.minutos for r in filtrada.context["historial"]], [25])
