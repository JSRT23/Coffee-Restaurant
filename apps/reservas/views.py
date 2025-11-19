from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.utils import timezone
from django.core.exceptions import ValidationError
from django_ratelimit.decorators import ratelimit

from django.utils.decorators import method_decorator
from datetime import datetime, timedelta, time as dt_time

from .models import Reserva, Mesa, Ubicacion, EstadoReserva
from .serializers import (
    ReservaSerializer,
    MesaSerializer,
    UbicacionSerializer,
    EstadoReservaSerializer,
    MisReservaSerializer,
)


@method_decorator(ratelimit(key='user', rate='5/d', method='POST'), name='post')
class ReservaCrearView(generics.CreateAPIView):
    serializer_class = ReservaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        hoy = timezone.now().date()
        reservas_hoy = Reserva.objects.filter(
            usuario=self.request.user, fecha=hoy
        ).count()
        if reservas_hoy >= 5:
            raise ValidationError(
                "Has alcanzado el límite de 5 reservas por día.")
        super().perform_create(serializer)


class MisReservasView(generics.ListAPIView):
    serializer_class = MisReservaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Reserva.objects
            .filter(usuario=self.request.user)
            .select_related('estado', 'mesa', 'mesa__ubicacion')
            .order_by("-fecha", "-hora_inicio")
        )


class MesasDisponiblesView(generics.ListAPIView):
    serializer_class = MesaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Min

        fecha = self.request.query_params.get("fecha")
        hora_inicio = self.request.query_params.get("hora_inicio")
        numero_personas = int(
            self.request.query_params.get("numero_personas", 1))
        ubicacion_id = self.request.query_params.get("ubicacion_id")

        if not (fecha and hora_inicio):
            return Mesa.objects.none()

        if numero_personas == 1:
            capacidad_objetivo = 2
        elif numero_personas <= 2:
            capacidad_objetivo = 2
        elif numero_personas <= 4:
            capacidad_objetivo = 4
        elif numero_personas <= 6:
            capacidad_objetivo = 6
        else:
            return Mesa.objects.none()

        hora_fin = (datetime.strptime(hora_inicio, "%H:%M") +
                    timedelta(minutes=30)).time()
        ocupadas = Reserva.objects.filter(
            fecha=fecha,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio,
        ).values_list("mesa_id", flat=True)

        qs = Mesa.objects.filter(
            activo=True,
            disponible=True,
            capacidad=capacidad_objetivo,
        ).exclude(id__in=ocupadas)

        if ubicacion_id:
            qs = qs.filter(ubicacion_id=ubicacion_id)

        if not qs.exists():
            siguiente_cap = (
                Mesa.objects.filter(
                    activo=True,
                    disponible=True,
                    capacidad__gt=capacidad_objetivo,
                )
                .aggregate(Min("capacidad"))["capacidad__min"]
            )
            if siguiente_cap:
                qs = Mesa.objects.filter(
                    activo=True,
                    disponible=True,
                    capacidad=siguiente_cap,
                ).exclude(id__in=ocupadas)
                if ubicacion_id:
                    qs = qs.filter(ubicacion_id=ubicacion_id)

        return qs.order_by("capacidad")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirmar_reserva_con_codigo(request):
    codigo = request.data.get("codigo")
    try:
        reserva = Reserva.objects.get(codigo_confirmacion=codigo.upper())
        if reserva.estado.nombre == "Confirmada":
            return Response({"detail": "Esta reserva ya está confirmada."}, status=400)
        reserva.estado = EstadoReserva.objects.get(nombre="Confirmada")
        reserva.save()
        return Response({"detail": "Reserva confirmada exitosamente."})
    except Reserva.DoesNotExist:
        return Response({"detail": "Código inválido."}, status=404)


class UbicacionListView(generics.ListCreateAPIView):
    serializer_class = UbicacionSerializer
    queryset = Ubicacion.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdminUser()]


class EstadoReservaListView(generics.ListCreateAPIView):
    serializer_class = EstadoReservaSerializer
    queryset = EstadoReserva.objects.all()

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdminUser()]


class ReservasMeseroPendientesHoyView(generics.ListAPIView):
    serializer_class = MisReservaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # ✅ Hora local del sistema
        ahora = timezone.localtime()
        hoy = ahora.date()
        hora_actual = ahora.time()

        return (
            Reserva.objects.filter(
                fecha=hoy,
                hora_inicio__gte=hora_actual,
                estado__nombre="Pendiente"
            )
            .select_related('usuario', 'mesa', 'mesa__ubicacion', 'estado')
            .order_by('hora_inicio')
        )
