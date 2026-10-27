# Projecto-Django

Django project for the Proyecto Estudio website.

## Requirements

- Python 3.12 or later
- Git

## Run locally

From this directory, create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create the database tables and start the development server:

```powershell
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The administrator and user pages are at `/administrador/` and `/usuario/`; Django admin is at `/admin/`.

For deployment, set `DJANGO_SECRET_KEY` to a new, private value and configure `DEBUG` and `ALLOWED_HOSTS` for the deployment environment. Do not use the local development fallback key in production.

## CAMBIOS A REALIZAR ##

-Pueden haber múltiples personas con el mismo nombre
-Profesor no tiene la capacidad de eliminar alumnos
