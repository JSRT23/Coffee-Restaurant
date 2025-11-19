from django.apps import AppConfig


class PedidosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pedidos'

    def ready(self):
        import apps.pedidos.signals  # 👈 asegura que cargue