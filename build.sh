#!/usr/bin/env bash
# Build script para Render - Django + DRF + Celery + Redis
set -o errexit  # Detener si hay error

# 1. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 2. Migraciones
python manage.py migrate

# 3. Crear superusuario automáticamente (si no existe)
echo "Creando superusuario AJS23..."

python << END
from django.contrib.auth import get_user_model
User = get_user_model()

username = "AJS23"
password = "Juan.2003"
email = "admin@example.com"

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, password=password, email=email)
    print("Superusuario creado correctamente.")
else:
    print("Superusuario YA existe, no se crea.")
END

# 4. Recolectar archivos estáticos
python manage.py collectstatic --noinput

