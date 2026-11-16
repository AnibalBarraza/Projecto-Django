"""Paginación reutilizable que conserva filtros y contexto del recorrido."""

from django.core.paginator import Paginator

TAMANO_PAGINA = 30


def paginar(objetos, parametros, nombre="pagina"):
    return Paginator(objetos, TAMANO_PAGINA).get_page(parametros.get(nombre))


def navegacion(pagina, parametros, nombre="pagina", ancla=""):
    def enlace(numero):
        filtros = parametros.copy()
        filtros[nombre] = numero
        return "?" + filtros.urlencode() + ("#" + ancla if ancla else "")

    return {
        "pagina": pagina,
        "anterior": (
            enlace(pagina.previous_page_number()) if pagina.has_previous() else None
        ),
        "siguiente": enlace(pagina.next_page_number()) if pagina.has_next() else None,
    }
