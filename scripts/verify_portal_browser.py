"""Browser smoke test with a disposable SQLite DB. Never connects to RDS.
Install optional tooling: python -m pip install -r requirements-dev.txt
Run: python scripts/verify_portal_browser.py
"""

import json
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import tempfile
import threading
from wsgiref.simple_server import make_server, WSGIRequestHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DJANGO_SETTINGS_MODULE"] = "Proyecto_Estudio.test_settings"


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def main():
    import django
    from django.conf import settings
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory(prefix="portal-db-") as temporary:
        settings.DATABASES["default"]["NAME"] = str(Path(temporary) / "qa.sqlite3")
        django.setup()
        from django.core.management import call_command
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django.contrib.staticfiles.handlers import StaticFilesHandler
        from django.core.wsgi import get_wsgi_application
        from django.db import connections
        from django.utils import timezone
        from AppEstudios.models import (
            Sala,
            Estudiante,
            Inscripcion,
            Materia,
            Calificacion,
            RegistroEstudio,
        )

        call_command("migrate", verbosity=0)
        User = get_user_model()
        password = "Qa-" + os.urandom(16).hex()
        teacher = User.objects.create_user("qa_teacher", password=password)
        group, _ = Group.objects.get_or_create(name="Profesores")
        teacher.groups.add(group)
        course = Sala.objects.create(
            profesor=teacher,
            nombre_profesor="Docente QA",
            asignatura="Matemática",
            seccion="A",
            semestre_actual=2,
            anio_actual=2026,
        )
        other = Sala.objects.create(
            profesor=teacher,
            nombre_profesor="Docente QA",
            asignatura="Física",
            seccion="B",
            semestre_actual=2,
            anio_actual=2026,
        )
        subject = Materia.objects.create(nombre="Matemática")
        for i, grade in enumerate([2, 3, 4.5, 5.2, 5.8, 6.1, 6.5, 7]):
            user = User.objects.create_user(f"qa_student_{i}", password=password)
            student = Estudiante.objects.create(
                usuario=user,
                nombre=f"Estudiante {i}",
                apellido="Prueba",
                edad=18 + i % 6,
                tiempo_viaje=Estudiante.TIEMPO_VIAJE_CHOICES[i % 4][0],
            )
            for room in [course, other]:
                Inscripcion.objects.create(estudiante=student, sala=room)
                for semester in [1, 2]:
                    Calificacion.objects.create(
                        sala=room,
                        estudiante=student,
                        materia=subject,
                        semestre=semester,
                        anio=2026,
                        nota=grade if room == course else max(1, grade - 1),
                    )
            RegistroEstudio.objects.create(
                estudiante=student,
                sala=course,
                fecha=timezone.localdate(),
                minutos=30 + i,
            )
        qa_student = Estudiante.objects.get(usuario__username="qa_student_0")
        RegistroEstudio.objects.create(
            estudiante=qa_student, sala=other, fecha=timezone.localdate(), minutos=40
        )
        for days in range(1, 25):
            if days % 3:
                RegistroEstudio.objects.create(
                    estudiante=qa_student,
                    sala=course,
                    fecha=timezone.localdate() - timedelta(days=days),
                    minutos=20 + days % 4 * 15,
                )
        connections.close_all()
        server = make_server(
            "127.0.0.1",
            0,
            StaticFilesHandler(get_wsgi_application()),
            handler_class=QuietHandler,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        artifacts = Path(tempfile.mkdtemp(prefix="portal-screenshots-"))
        errors = []
        try:
            with sync_playwright() as playwright:
                executable = next(
                    (
                        p
                        for p in [
                            Path(
                                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
                            ),
                            Path(
                                r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                            ),
                        ]
                        if p.exists()
                    ),
                    None,
                )
                browser = playwright.chromium.launch(
                    executable_path=str(executable) if executable else None,
                    headless=True,
                )
                page = browser.new_page(
                    viewport={"width": 1365, "height": 900}, locale="es-CL"
                )
                page.on("pageerror", lambda error: errors.append(str(error)))

                def screenshot(filename):
                    page.evaluate("window.scrollTo(0, 0)")
                    page.screenshot(path=str(artifacts / filename), full_page=True)

                def login(username):
                    page.goto(base + "/ingresar/")
                    page.locator("[name=username]").fill(username)
                    page.locator("[name=password]").fill(password)
                    page.locator("button[type=submit]").first.click()
                    page.wait_for_url("**/tablero/")

                def switch_account(username):
                    page.get_by_role(
                        "link", name="Cambiar de cuenta", exact=True
                    ).click()
                    page.wait_for_url("**/cambiar-cuenta/")
                    assert page.locator("h1").inner_text() == "Cambiar de cuenta"
                    page.locator("[name=username]").fill(username)
                    page.locator("[name=password]").fill(password)
                    page.get_by_role(
                        "button", name="Entrar con esta cuenta", exact=True
                    ).click()
                    page.wait_for_url("**/tablero/")
                    assert page.locator(".account-name").inner_text() == username

                page.goto(base + "/")
                assert "Cada avance cuenta." in page.locator("h1").inner_text()
                screenshot("inicio-desktop.png")
                login("qa_teacher")
                page.locator('[data-open-dialog="crear-curso"]').click()
                assert page.locator("dialog#crear-curso").is_visible()
                page.keyboard.press("Escape")
                assert not page.locator("dialog#crear-curso").is_visible()
                page.locator('[data-open-dialog="crear-curso"]').click()
                dialog = page.locator("dialog#crear-curso")
                screenshot("crear-curso-dialogo.png")
                dialog.locator("[name=asignatura]").fill(
                    "Curso creado desde el tablero"
                )
                dialog.locator("[name=seccion]").fill("Prueba")
                dialog.locator("[name=semestre_actual]").fill("2")
                dialog.locator("[name=anio_actual]").fill("2026")
                dialog.get_by_role("button", name="Crear curso", exact=True).click()
                page.wait_for_url("**/cursos/**")
                assert (
                    "Curso creado desde el tablero" in page.locator("h1").inner_text()
                )
                page.goto(base + "/tablero/")

                screenshot("tablero-profesor.png")
                switch_account("qa_student_0")
                assert page.locator('[data-open-dialog="crear-curso"]').count() == 0
                switch_account("qa_teacher")
                assert page.locator('[data-open-dialog="crear-curso"]').is_visible()
                assert (
                    "Curso creado desde el tablero" in page.locator("main").inner_text()
                )

                page.goto(base + "/rendimiento/?semestre=2&anio=2026")
                page.locator("[data-chart=cursos] svg a").first.wait_for()
                original = page.locator(
                    "[data-chart=cursos] svg a"
                ).first.get_attribute("aria-label")
                page.locator("[data-chart=cursos] select").select_option("desc")
                assert page.locator("[data-chart=cursos] svg a").count() == 2
                assert (
                    page.locator("[data-chart=cursos] svg a").first.get_attribute(
                        "aria-label"
                    )
                    != original
                )
                assert page.locator("[data-chart=evolucion] svg circle").count() == 4
                screenshot("rendimiento-desktop.png")
                page.locator("[data-chart=evolucion] svg a").first.click()
                page.wait_for_url("**/rendimiento/?semestre=1&anio=2026")
                assert "Semestre 1" in page.locator("[data-chart=cursos]").inner_text()
                page.goto(base + "/rendimiento/?semestre=2&anio=2026")
                page.locator("[data-chart=cursos] select").select_option("desc")
                page.locator("[data-chart=cursos] svg a").first.click()
                page.wait_for_url("**/calificaciones/?semestre=2&anio=2026")
                screenshot("calificaciones-profesor.png")
                assert not page.locator(".note-entry-form").is_visible()
                page.locator(".note-entry > summary").click()
                assert page.locator(".note-entry-form").is_visible()
                page.locator(".note-entry > summary").click()
                for chart_id in (
                    "historia-estudiantes",
                    "promedio-cantidad",
                    "cambio-promedios",
                ):
                    page.locator(f"[data-chart={chart_id}] svg a").first.wait_for()
                page.evaluate("window.explorationMarker = 'same-document'")
                page.locator("[data-chart=distribucion] svg a").nth(1).click()
                page.wait_for_url("**banda=1#seleccion")
                assert page.evaluate("window.explorationMarker") == "same-document"
                assert page.locator("[data-chart=estudiantes] svg a").count() == 1
                assert page.locator("[data-chart=promedio-cantidad] svg a").count() == 1
                assert (
                    "Mostrando estudiantes" in page.locator("#seleccion").inner_text()
                )
                page.locator("[data-chart=estudiantes] svg a").first.click()
                page.wait_for_url("**/estudiantes/**")
                assert "semestre=2" in page.url and "anio=2026" in page.url
                assert "banda%3D1" in page.url
                page.locator(".back-link").click()
                page.wait_for_url("**banda=1#estudiantes-grafico")
                assert page.locator("[data-chart=estudiantes] svg a").count() == 1
                page.locator("#seleccion a").click()
                page.wait_for_function("!document.querySelector('#seleccion')")
                assert page.locator("[data-chart=estudiantes] svg a").count() == 8
                page.go_back()
                page.wait_for_function(
                    "!!document.querySelector('#seleccion') && !document.querySelector('main[aria-busy]')"
                )
                assert page.locator("[data-chart=estudiantes] svg a").count() == 1
                page.locator("[data-chart=historia-estudiantes] svg a").last.click()
                page.wait_for_url("**/estudiantes/**")
                mark = page.locator("[data-chart=notas] svg a").first
                mark.focus()
                page.keyboard.press("Enter")
                page.wait_for_function(
                    "document.querySelector('details[id^=detalle-]').open"
                )
                screenshot("ficha-desktop.png")
                page.locator("[data-chart=historia-curso] svg a").first.click()
                page.wait_for_url("**/estudiantes/**semestre=1&anio=2026*")
                assert (
                    "Estudiante 0 Prueba"
                    in page.locator(".section-heading h2").inner_text()
                )
                page.goto(base + f"/cursos/{course.pk}/calificaciones/?semestre=2&anio=2026")
                for chart_id in ("promedio-cantidad", "cambio-promedios"):
                    page.locator(f"[data-chart={chart_id}] svg a").first.click()
                    page.wait_for_url("**/estudiantes/**")
                    assert page.locator("[data-chart=cambio-promedios] details").get_attribute("open") is not None
                    page.locator(".back-link").click()
                    page.wait_for_url("**/calificaciones/**")
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                matrix = page.locator("[data-chart=historia-estudiantes] .chart-canvas")
                assert matrix.evaluate("node => node.scrollWidth > node.clientWidth")
                screenshot("exploracion-profesor-mobile.png")
                page.set_viewport_size({"width": 1365, "height": 900})
                page.goto(base + f"/cursos/{course.pk}/resumen/")
                page.locator(".course-context > summary").click()
                page.locator("[data-chart=edades] svg a").first.wait_for()
                screenshot("resumen-profesor.png")
                page.locator("[data-chart=edades] svg a").first.click()
                page.wait_for_url("**edad=*")
                assert page.locator("#lista-estudiantes a").count() >= 1
                page.locator(".logout button").click()
                page.wait_for_url("**/ingresar/")

                def seed_more_notes():
                    try:
                        first_student = Estudiante.objects.get(
                            usuario__username="qa_student_0"
                        )
                        Calificacion.objects.bulk_create(
                            [
                                Calificacion(
                                    sala=course,
                                    estudiante=first_student,
                                    materia=subject,
                                    nota=2,
                                    semestre=2,
                                    anio=2026,
                                )
                                for _ in range(30)
                            ]
                        )
                    finally:
                        connections.close_all()

                with ThreadPoolExecutor(max_workers=1) as executor:
                    executor.submit(seed_more_notes).result()
                login("qa_student_0")
                page.goto(base + "/estudio/")
                page.locator("[data-chart=constancia] svg a").first.wait_for()
                screenshot("estudio-desktop.png")
                assert page.locator("[data-chart=estudio-cursos] svg path").count() == 2
                # Click inside the first ring segment, not its empty central hole.
                donut = page.locator("[data-chart=estudio-cursos]")
                donut.scroll_into_view_if_needed()
                position = donut.evaluate("""section => {
                    const data = JSON.parse(section.querySelector('script').textContent);
                    const svg = section.querySelector('svg');
                    const total = data.points.reduce((sum, point) => sum + point.value, 0);
                    const angle = -Math.PI / 2 + Math.PI * data.points[0].value / total;
                    const point = new DOMPoint(svg.viewBox.baseVal.width / 2 + 84 * Math.cos(angle), 130 + 84 * Math.sin(angle)).matrixTransform(svg.getScreenCTM());
                    return {x: point.x, y: point.y};
                }""")
                page.mouse.click(position["x"], position["y"])
                page.wait_for_url("**/calificaciones/")
                page.goto(base + "/estudio/")
                page.locator("[data-chart=constancia] svg a").first.click()
                page.wait_for_url("**fecha=*#historial")
                page.locator("[data-chart=estudio-dias] svg a").last.click()
                page.wait_for_url("**fecha=*#historial")
                assert "Historial filtrado" in page.locator("#historial").inner_text()
                page.set_viewport_size({"width": 390, "height": 844})
                page.goto(base + "/rendimiento/?semestre=2&anio=2026")
                page.locator("[data-chart=cursos] svg a").first.wait_for()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                screenshot("rendimiento-mobile.png")
                page.locator("[data-chart=cursos] svg a").first.click()
                page.wait_for_url("**/calificaciones/**")
                page.locator("[data-chart=notas] svg a").first.click()
                assert (
                    page.locator("details[id^=detalle-]").first.get_attribute("open")
                    is not None
                )
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                screenshot("notas-mobile.png")
                page.goto(
                    base + f"/cursos/{course.pk}/calificaciones/?semestre=2&anio=2026"
                )
                assert page.locator("#tabla-notas tbody tr").count() == 30
                page.locator(".pagination").first.get_by_role(
                    "link", name="Siguiente →"
                ).click()
                page.wait_for_url("**pagina=2#tabla-notas")
                assert page.locator("#tabla-notas tbody tr").count() == 1
                assert "Nota 31" in page.locator(
                    "[data-chart=notas] svg a"
                ).first.get_attribute("aria-label")
                page.locator("[data-chart=notas] svg a").first.click()
                assert (
                    page.locator("details[id^=detalle-]").first.get_attribute("open")
                    is not None
                )
                page.goto(base + "/estudio/")
                page.locator("[data-chart=constancia] svg a").first.wait_for()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                screenshot("estudio-mobile.png")
                page.locator("[data-chart=constancia] svg a").last.click()
                page.wait_for_url("**fecha=*#historial")
                assert page.locator("#historial").get_attribute("open") is not None
                page.goto(base + "/")
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                screenshot("inicio-mobile.png")
                page.goto(base + "/tablero/")
                switch_account("qa_teacher")
                page.wait_for_url("**/tablero/")
                assert page.locator('[data-open-dialog="crear-curso"]').is_visible()
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                )
                screenshot("tablero-mobile.png")
                assert not errors, errors
                browser.close()
                print(
                    json.dumps(
                        {
                            "result": "OK",
                            "flows": [
                                "teacher course/range/student/note",
                                "keyboard note detail",
                                "student study/day/history",
                                "mobile course/note",
                                "paginated notes and chart details",
                                "histogram and profile filters",
                                "donut and heatmap drilldown",
                                "public landing and course dialog",
                                "separate teacher/student account authentication",
                            ],
                            "javascript_errors": errors,
                            "screenshots": str(artifacts),
                        },
                        ensure_ascii=False,
                    )
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            connections.close_all()


if __name__ == "__main__":
    main()
