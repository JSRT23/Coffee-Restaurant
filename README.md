# ☕ Coffee Restaurant — Backend (Krazz Ice)

API REST del sistema de **Krazz Ice / Coffee & Rest**: usuarios con roles, inventario, pedidos y panel de administración.

![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-JWT-A30000)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

## Módulos

| App | Responsabilidad |
|---|---|
| `usuarios` | Usuario propio con roles `ADMIN`, `CLIENTE`, `MESERO`, `COCINERO`; login JWT |
| `inventario` | Productos e insumos |
| `pedidos` | Pedidos y su flujo (cliente → mesero → cocina) |
| `dashboard_admin` | Métricas para administración |

Frontend: [Krazz-Ice](https://github.com/JSRT23/Krazz-Ice).

## Variables de entorno

Copia `.env.example` a `.env`.

| Variable | Descripción |
|---|---|
| `SECRET_KEY`, `DEBUG` | Configuración de Django |
| `ALLOWED_HOSTS` | Hosts extra permitidos (separados por coma) |
| `CORS_ALLOWED_ORIGINS` | Orígenes extra permitidos |
| `DATABASE_URL` | Opcional; por defecto SQLite (`Krazz.sqlite3`) |

## Cómo correrlo

### Con Docker

```bash
git clone https://github.com/JSRT23/Coffee-Restaurant.git
cd Coffee-Restaurant
cp .env.example .env
docker compose up --build        # http://localhost:8000
```

En el primer arranque se copia `Krazz.sqlite3` a un volumen persistente (`/data`).

### Sin Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # mysqlclient necesita libmysqlclient-dev
python manage.py migrate
python manage.py runserver
```

## Notas

- `requirements.txt` quedó en UTF-8 (antes estaba en UTF-16 y `pip` no lo leía).
- Celery y Redis aparecen en `requirements.txt` pero hoy no se usan.
