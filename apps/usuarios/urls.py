from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    ClienteRegistroView,
    MeseroCrearView,
    UserMeView,
    buscar_cliente_por_username,
    CustomTokenObtainPairView,
)

urlpatterns = [
    #  Autenticación y registro
    path('auth/registro/', ClienteRegistroView.as_view(), name='cliente-registro'),
    path('auth/crear-mesero/', MeseroCrearView.as_view(), name='crear-mesero'),
    # Login con duración de sesión personalizada por rol
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    # Refresh del token (para extender sesión)
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Obtener información del usuario actual
    path('auth/me/', UserMeView.as_view(), name='me'),
    # Buscar cliente por username
    path("auth/buscar-cliente/<str:username>/",
         buscar_cliente_por_username, name="buscar_cliente_por_username"),
]
