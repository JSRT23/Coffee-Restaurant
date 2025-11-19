from django.urls import path
from .views import *
urlpatterns = [
    # Estados
    path("estados/", EstadoListCreateView.as_view(), name="estado-list-create"),
    path("estados/<int:pk>/", EstadoDetailView.as_view(), name="estado-detail"),

    # Métodos de pago
    path("metodos-pago/", MetodoPagoListCreateView.as_view(),
         name="metodo-pago-list-create"),
    path("metodos-pago/<int:pk>/", MetodoPagoDetailView.as_view(),
         name="metodo-pago-detail"),

    # Pedidos
    path("pedidos/", PedidoListCreateView.as_view(), name="pedido-list-create"),
    path("pedidos/<int:pk>/", PedidoDetailView.as_view(), name="pedido-detail"),

    # Detalles
    path("detalles/", DetallePedidoListCreateView.as_view(),
         name="detalle-list-create"),
    path("detalles/<int:pk>/", DetallePedidoDetailView.as_view(),
         name="detalle-detail"),

    # Variantes disponibles
    path("variantes-disponibles/", VariantesDisponiblesListView.as_view(),
         name="variantes-disponibles"),

    # Pedidos en cocina
    path("pedidos/cocina/", PedidosCocinaListView.as_view(), name="pedidos-cocina"),

    # Mis pedidos últimos 15 días
    path("mis-pedidos/ultimos-15-dias/",
         PedidosUltimos15DiasView.as_view(), name="mis-pedidos-15d"),

    # Mis pedidos TODOS
    path("mis-pedidos/todos/", MisPedidosTodosView.as_view(),
         name="mis-pedidos-todos"),

    # Estado en tiempo real
    path("pedidos/estado/<int:pk>/",
         PedidoEstadoView.as_view(), name="pedido-estado"),
]
