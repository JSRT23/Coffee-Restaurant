from rest_framework import generics, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.timezone import localdate
from django.core.exceptions import ValidationError
from .models import Pedido, DetallePedido, EstadoPedido, MetodoPago
from .serializers import (
    PedidoSerializer,
    DetallePedidoSerializer,
    EstadoSerializer,
    MetodoPagoSerializer,
)
from apps.inventario.models import ProductoVariante
from apps.inventario.serializers import ProductoVarianteSerializer
from django.utils import timezone
from datetime import timedelta
from django.db.models import Prefetch


# ================================
# ESTADOS Y MÉTODOS DE PAGO
# ================================

class EstadoListCreateView(generics.ListCreateAPIView):
    queryset = EstadoPedido.objects.all()
    serializer_class = EstadoSerializer


class EstadoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EstadoPedido.objects.all()
    serializer_class = EstadoSerializer


class MetodoPagoListCreateView(generics.ListCreateAPIView):
    queryset = MetodoPago.objects.all()
    serializer_class = MetodoPagoSerializer


class MetodoPagoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MetodoPago.objects.all()
    serializer_class = MetodoPagoSerializer


# ================================
# LISTAR Y CREAR PEDIDOS
# ================================

class PedidoListCreateView(generics.ListCreateAPIView):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        hoy = localdate()
        user = self.request.user

        if user.rol in ["MESERO", "COCINERO"]:
            # Mesero ve todos los del día
            return (
                Pedido.objects.filter(fecha_pedido__date=hoy)
                .select_related("cliente", "empleado", "estado", "metodo_pago")
                .prefetch_related(
                    Prefetch(
                        "detalles",
                        queryset=DetallePedido.objects.select_related(
                            "variante", "variante__producto"
                        ),
                    )
                )
                .order_by("-id")
            )
        else:
            # Cliente (o cualquier otro rol) solo ve los suyos
            return (
                Pedido.objects.filter(
                    fecha_pedido__date=hoy,
                    cliente=user
                )
                .select_related("cliente", "empleado", "estado", "metodo_pago")
                .prefetch_related(
                    Prefetch(
                        "detalles",
                        queryset=DetallePedido.objects.select_related(
                            "variante", "variante__producto"
                        ),
                    )
                )
                .order_by("-id")
            )

    def perform_create(self, serializer):
        empleado = self.request.user if self.request.user.is_authenticated else None
        serializer.save(empleado=empleado)


# ================================
# DETALLE, EDITAR Y ELIMINAR PEDIDO
# ================================

class PedidoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = (
        Pedido.objects.all()
        .select_related("cliente", "empleado", "estado", "metodo_pago")
        .prefetch_related(
            Prefetch(
                "detalles",
                queryset=DetallePedido.objects.select_related(
                    "variante", "variante__producto"
                ),
            )
        )
    )
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_update(self, serializer):
        pedido = serializer.instance

        if pedido.estado.nombre in ["Entregado", "Cancelado"]:
            raise ValidationError("No se puede editar un pedido finalizado.")

        old_estado = pedido.estado.nombre
        new_estado_obj = serializer.validated_data.get("estado", pedido.estado)

        super().perform_update(serializer)

        new_estado = new_estado_obj.nombre

        if old_estado != "Entregado" and new_estado == "Entregado":
            pedido.entregar()
        elif old_estado != "Cancelado" and new_estado == "Cancelado":
            pedido.cancelar()


# ================================
# ESTADO ACTUAL DEL PEDIDO
# ================================

class PedidoEstadoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            pedido = Pedido.objects.get(pk=pk, cliente=request.user)
            return Response({
                "id": pedido.id,
                "estado": pedido.estado.nombre
            })
        except Pedido.DoesNotExist:
            return Response({"error": "Pedido no encontrado"}, status=404)


# ================================
# DETALLES DE PEDIDO
# ================================

class DetallePedidoListCreateView(generics.ListCreateAPIView):
    serializer_class = DetallePedidoSerializer
    queryset = DetallePedido.objects.all().select_related("pedido", "variante")
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        pedido_id = self.request.data.get("pedido_id")
        tipo_pedido = self.request.data.get("tipo", "interno")

        if not pedido_id:
            pedido = Pedido.objects.filter(
                cliente=user, estado__nombre="Pendiente"
            ).first()

            if not pedido:
                estado_pendiente, _ = EstadoPedido.objects.get_or_create(
                    nombre="Pendiente"
                )
                metodo_efectivo, _ = MetodoPago.objects.get_or_create(
                    nombre="Efectivo en tienda",
                    defaults={
                        "descripcion": "Pago en efectivo al reclamar en tienda"
                    },
                )
                pedido = Pedido.objects.create(
                    cliente=user,
                    empleado=user,
                    estado=estado_pendiente,
                    metodo_pago=metodo_efectivo,
                    tipo=tipo_pedido,
                )
        else:
            pedido = Pedido.objects.get(id=pedido_id)

        if pedido.estado.nombre in ["Entregado", "Cancelado"]:
            raise ValidationError(
                "No se puede agregar productos a un pedido finalizado.")

        serializer.save(pedido=pedido)


class DetallePedidoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DetallePedido.objects.all().select_related("pedido", "variante")
    serializer_class = DetallePedidoSerializer
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        detalle = serializer.instance
        if detalle.pedido.estado.nombre in ["Entregado", "Cancelado"]:
            raise ValidationError("No se puede editar un detalle finalizado.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.pedido.estado.nombre in ["Entregado", "Cancelado"]:
            raise ValidationError(
                "No se puede eliminar un detalle finalizado.")
        super().perform_destroy(instance)


# ================================
# PRODUCTOS DISPONIBLES
# ================================

class VariantesDisponiblesListView(generics.ListAPIView):
    serializer_class = ProductoVarianteSerializer

    def get_queryset(self):
        return ProductoVariante.objects.filter(activo=True, stock__gt=0)


# ================================
# PANEL DE COCINA
# ================================

class PedidosCocinaListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PedidoSerializer

    def get_queryset(self):
        hoy = localdate()

        return (
            Pedido.objects.filter(
                fecha_pedido__date=hoy,
                estado__nombre__in=["Pendiente", "En cocina"]
            )
            .select_related("estado", "cliente", "empleado", "metodo_pago")
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetallePedido.objects.select_related(
                        "variante", "variante__producto"
                    ),
                )
            )
            .order_by("fecha_pedido")
        )


# ================================
# PEDIDOS ÚLTIMOS 15 DÍAS
# ================================

class PedidosUltimos15DiasView(generics.ListAPIView):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        ahora = timezone.now()
        hace_15 = ahora - timedelta(days=15)

        return (
            Pedido.objects.filter(cliente=user, fecha_pedido__gte=hace_15)
            .select_related("cliente", "empleado", "estado", "metodo_pago")
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetallePedido.objects.select_related(
                        "variante", "variante__producto"
                    ),
                )
            )
            .order_by("-fecha_pedido")
        )


# ================================
# MIS PEDIDOS COMPLETOS
# ================================

class MisPedidosTodosView(generics.ListAPIView):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Pedido.objects.filter(cliente=self.request.user)
            .select_related("cliente", "empleado", "estado", "metodo_pago")
            .prefetch_related(
                Prefetch(
                    "detalles",
                    queryset=DetallePedido.objects.select_related(
                        "variante", "variante__producto"
                    ),
                )
            )
            .order_by("-fecha_pedido")
        )
