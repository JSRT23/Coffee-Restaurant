from django.urls import path
from . import views
urlpatterns = [
    # Reservas
    path('crear/', views.ReservaCrearView.as_view(), name='crear_reserva'),
    path('mis/', views.MisReservasView.as_view(), name='mis_reservas'),

    # Mesas disponibles
    path('mesas-disponibles/', views.MesasDisponiblesView.as_view(),
         name='mesas_disponibles'),

    # Admin: ubicaciones y estados
    path('ubicaciones/', views.UbicacionListView.as_view(), name='ubicaciones'),
    path('estados/', views.EstadoReservaListView.as_view(), name='estados_reserva'),
    path('confirmar-con-codigo/', views.confirmar_reserva_con_codigo,
         name='confirmar_con_codigo'),
    path('mesero-pendientes/', views.ReservasMeseroPendientesHoyView.as_view(),
         name='reservas_mesero_pendientes'),
]
