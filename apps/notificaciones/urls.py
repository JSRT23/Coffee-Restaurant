from django.urls import path
from .views import MisNotificacionesView, MarcarLeidaView

urlpatterns = [
    path('mis/', MisNotificacionesView.as_view(), name='mis-notificaciones'),
    path('<int:pk>/leer/', MarcarLeidaView.as_view(), name='notificacion-leer'),
]
