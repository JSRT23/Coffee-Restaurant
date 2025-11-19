from datetime import timedelta
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Usuario
from .serializers import RegistroSerializer, MeseroCrearSerializer
from .permissions import EsAdmin


# ------------------------------------------------------------
# 🔹 LOGIN PERSONALIZADO CON DURACIÓN SEGÚN ROL
# ------------------------------------------------------------
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Genera tokens JWT con distinta duración según el rol del usuario.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["rol"] = getattr(user, "rol", "CLIENTE")
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        rol = getattr(user, "rol", "CLIENTE").upper()

        # Token base
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # 🔒 Duración personalizada por rol
        if rol in ["COCINERO", "COCINA"]:
            access.set_exp(lifetime=timedelta(hours=8))
            refresh.set_exp(lifetime=timedelta(days=7))
        elif rol in ["MESERO", "CAJERO"]:
            access.set_exp(lifetime=timedelta(minutes=45))
            refresh.set_exp(lifetime=timedelta(hours=12))
        else:  # CLIENTE o ADMIN
            access.set_exp(lifetime=timedelta(minutes=60))
            refresh.set_exp(lifetime=timedelta(days=1))

        # Datos del token
        data["access"] = str(access)
        data["refresh"] = str(refresh)
        data["user"] = {
            "id": user.id,
            "username": user.username,
            "rol": rol,
        }

        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ------------------------------------------------------------
# 🔹 REGISTRO DE CLIENTES Y MESEROS
# ------------------------------------------------------------
class ClienteRegistroView(generics.CreateAPIView):
    queryset = Usuario.objects.filter(rol='CLIENTE')
    serializer_class = RegistroSerializer
    permission_classes = [AllowAny]


class MeseroCrearView(generics.CreateAPIView):
    queryset = Usuario.objects.filter(rol='MESERO')
    serializer_class = MeseroCrearSerializer
    permission_classes = [IsAuthenticated, EsAdmin]


# ------------------------------------------------------------
# 🔹 PERFIL DEL USUARIO AUTENTICADO
# ------------------------------------------------------------
class UserMeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "rol": getattr(user, "rol", "CLIENTE"),
        })


# ------------------------------------------------------------
# 🔹 BÚSQUEDA DE CLIENTES POR USERNAME
# ------------------------------------------------------------
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def buscar_cliente_por_username(request, username):
    """
    Permite al mesero o admin buscar un cliente por su nombre de usuario.
    Requiere autenticación JWT.
    """
    try:
        cliente = Usuario.objects.get(username=username, rol="CLIENTE")
        return Response(
            {"id": cliente.id, "username": cliente.username, "rol": cliente.rol},
            status=status.HTTP_200_OK,
        )
    except Usuario.DoesNotExist:
        return Response(
            {"detail": f"No se encontró ningún cliente con el username '{username}'."},
            status=status.HTTP_404_NOT_FOUND,
        )
