from .settings import *

# This module never opens a connection to RDS. Tests use an in-memory database.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
