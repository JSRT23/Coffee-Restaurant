from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from rest_framework import viewsets, permissions, status, serializers, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import (
    EstadoCredito, Credito, TipoMovimiento, MovimientoCredito,
    AuditoriaCredito, EstadoSolicitud, SolicitudAcreditacion
)
from .serializers import (
    EstadoCreditoSerializer, TipoMovimientoSerializer, CreditoSerializer,
    MovimientoCreditoSerializer, AuditoriaCreditoSerializer,
    EstadoSolicitudSerializer, SolicitudAcreditacionSerializer
)
from .filters import MovimientoFilter


# ---------- ADMIN ----------
class EstadoCreditoViewSet(viewsets.ModelViewSet):
    queryset = EstadoCredito.objects.all()
    serializer_class = EstadoCreditoSerializer
    permission_classes = [permissions.IsAdminUser]


class TipoMovimientoViewSet(viewsets.ModelViewSet):
    queryset = TipoMovimiento.objects.all()
    serializer_class = TipoMovimientoSerializer
    permission_classes = [permissions.IsAdminUser]


# ---------- CRÉDITOS CLIENTE ----------
class CreditoViewSet(viewsets.ModelViewSet):
    serializer_class = CreditoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Credito.objects.all()
        user = self.request.user
        if user.is_staff:
            return qs.select_related("cliente", "estado")
        return qs.filter(cliente=user).select_related("cliente", "estado")

    @action(detail=True, methods=["post"])
    def consumir(self, request, pk=None):
        credito = self.get_object()
        if credito.cliente != request.user:
            raise PermissionDenied("No es tu crédito.")
        monto = request.data.get("monto")
        detalle = request.data.get("detalle", "")
        try:
            credito.consumir(float(monto), detalle)
            AuditoriaCredito.objects.create(
                credito=credito,
                usuario=request.user,
                accion="Consumo",
                detalle=f"Consumo de {monto}. {detalle}",
            )
            return Response({"mensaje": f"Consumo de {monto} registrado."})
        except ValidationError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def pagar(self, request, pk=None):
        credito = self.get_object()
        if credito.cliente != request.user:
            raise PermissionDenied("No es tu crédito.")
        monto = request.data.get("monto")
        detalle = request.data.get("detalle", "")
        try:
            credito.pagar(float(monto), detalle)
            AuditoriaCredito.objects.create(
                credito=credito,
                usuario=request.user,
                accion="Pago",
                detalle=f"Pago de {monto}. {detalle}",
            )
            return Response({"mensaje": f"Pago de {monto} registrado."})
        except ValidationError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def movimientos(self, request, pk=None):
        credito = self.get_object()
        qs = MovimientoCredito.objects.filter(
            credito=credito).select_related("tipo")
        filtered = MovimientoFilter(request.GET, queryset=qs).qs
        page = self.paginate_queryset(filtered)
        if page is not None:
            serializer = MovimientoCreditoSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MovimientoCreditoSerializer(filtered, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def auditorias(self, request, pk=None):
        credito = self.get_object()
        qs = AuditoriaCredito.objects.filter(
            credito=credito).order_by("-fecha")
        serializer = AuditoriaCreditoSerializer(qs, many=True)
        return Response(serializer.data)


class MovimientoCreditoViewSet(viewsets.ModelViewSet):
    serializer_class = MovimientoCreditoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MovimientoFilter

    def get_queryset(self):
        user = self.request.user
        qs = MovimientoCredito.objects.select_related(
            "credito__cliente", "tipo")
        if user.is_staff:
            return qs
        return qs.filter(credito__cliente=user)


class AuditoriaCreditoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditoriaCreditoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = AuditoriaCredito.objects.select_related(
            "usuario", "credito__cliente")
        if user.is_staff:
            return qs
        return qs.filter(usuario=user)


# ---------- ACREDITACIÓN ----------
class EstadoSolicitudViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EstadoSolicitud.objects.all()
    serializer_class = EstadoSolicitudSerializer
    permission_classes = [IsAuthenticated]


class SolicitudAcreditacionViewSet(viewsets.ModelViewSet):
    serializer_class = SolicitudAcreditacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return SolicitudAcreditacion.objects.all().select_related("cliente", "estado")
        return SolicitudAcreditacion.objects.filter(cliente=user).select_related("cliente", "estado")

    def perform_create(self, serializer):
        if SolicitudAcreditacion.objects.filter(
            cliente=self.request.user,
            estado__nombre__in=["En revisión", "Aprobado"],
            credito_resultante__isnull=True
        ).exists():
            raise serializers.ValidationError(
                "Ya tienes una solicitud en curso.")
        estado_pendiente, _ = EstadoSolicitud.objects.get_or_create(
            nombre="En revisión")
        serializer.save(cliente=self.request.user, estado=estado_pendiente)

    @action(detail=True, methods=["patch"], permission_classes=[permissions.IsAdminUser])
    def responder(self, request, pk=None):
        """
        Cambia el estado de la solicitud.
        Si es "Aprobado"  → crea el crédito.
        Si es "Rechazado" → guarda fecha de rechazo y avisa al cliente.
        """
        solicitud = self.get_object()
        nuevo_estado_nombre = request.data.get("estado")
        observaciones = request.data.get("observaciones_staff", "")

        try:
            nuevo_estado = EstadoSolicitud.objects.get(
                nombre=nuevo_estado_nombre)
        except EstadoSolicitud.DoesNotExist:
            return Response({"error": "Estado inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if solicitud.estado.nombre != "En revisión":
            return Response({"error": "La solicitud ya fue respondida."}, status=status.HTTP_400_BAD_REQUEST)

        solicitud.estado = nuevo_estado
        solicitud.observaciones_staff = observaciones
        solicitud.fecha_respuesta = timezone.now()

        if nuevo_estado.nombre == "Aprobado":
            estado_activo, _ = EstadoCredito.objects.get_or_create(
                nombre="Activo")
            credito = Credito.objects.create(
                cliente=solicitud.cliente,
                limite=solicitud.monto_solicitado,
                estado=estado_activo
            )
            solicitud.credito_resultante = credito
            mensaje = "Solicitud aprobada. Tu crédito ya está activo."

        elif nuevo_estado.nombre == "Rechazado":
            solicitud.fecha_rechazo = timezone.now()
            mensaje = "Tu solicitud fue rechazada. Podés volver a intentarlo en 15 días."
        else:
            mensaje = f"Solicitud {nuevo_estado_nombre.lower()}."

        solicitud.save()
        return Response({"mensaje": mensaje})


# ---------- MESERO: LISTAR CRÉDITOS + ABONO ----------
class CreditoListMeseroView(generics.ListAPIView):
    """
    Lista todos los créditos (solo lectura) con filtro opcional por username.
    """
    serializer_class = CreditoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Credito.objects.select_related("cliente", "estado").all()
        username = self.request.query_params.get("username", "")
        if username:
            qs = qs.filter(cliente__username__icontains=username)
        return qs.order_by("-fecha_inicio")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def registrar_abono_mesero(request):
    """
    Registra un abono (pago) sobre un crédito existente.
    Body: { "credito_id": 12, "monto": 50.00, "detalle": "Abono en caja" }
    """
    credito_id = request.data.get("credito_id")
    monto = request.data.get("monto")
    detalle = request.data.get("detalle", "Abono en caja")

    if not credito_id or not monto:
        return Response({"error": "Faltan campos obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        monto = float(monto)
        if monto <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return Response({"error": "Monto inválido."}, status=status.HTTP_400_BAD_REQUEST)

    credito = get_object_or_404(Credito, pk=credito_id)

    # Crear movimiento de tipo "Pago"
    tipo_pago, _ = TipoMovimiento.objects.get_or_create(nombre="Pago")
    mov = credito.movimientos.create(
        tipo=tipo_pago,
        monto=monto,
        detalle=detalle
    )

    return Response({
        "mensaje": f"Abono de ${monto} registrado.",
        "movimiento": MovimientoCreditoSerializer(mov).data
    }, status=status.HTTP_201_CREATED)
