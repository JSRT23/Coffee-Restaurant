#!/usr/bin/env bash
# Build script para Render - Django + DRF + Celery + Redis
set -o errexit  # Detener si hay error

# 1. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 2. Migraciones
python manage.py migrate



