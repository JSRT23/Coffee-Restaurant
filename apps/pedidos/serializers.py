from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import Pedido, DetallePedido, EstadoPedido, MetodoPago
from apps.inventario.models import ProductoVariante


# ===========================
#   ESTADO
# ===========================
class EstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoPedido
        fields = ["id", "nombre", "descripcion"]


# ===========================
#   MÉTODO DE PAGO
# ===========================
class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetodoPago
        fields = ["id", "nombre", "descripcion"]


# ===========================
#   PRODUCTO VARIANTE
# ===========================
class ProductoVarianteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(
        source="producto.nombre", read_only=True)
    nombre_completo = serializers.SerializerMethodField()
    imagen_variante = serializers.ImageField(source="imagen", read_only=True)
    imagen_producto = serializers.ImageField(
        source="producto.imagen", read_only=True)

    class Meta:
        model = ProductoVariante
        fields = [
            "id",
            "producto_nombre",
            "nombre_variante",
            "nombre_completo",
            "imagen_variante",
            "imagen_producto",
        ]

    def get_nombre_completo(self, obj):
        if obj.producto:
            return f"{obj.producto.nombre} - {obj.nombre_variante}"
        return obj.nombre_variante


# ===========================
#   DETALLE PEDIDO
# ===========================
class DetallePedidoSerializer(serializers.ModelSerializer):
    variante = ProductoVarianteSerializer(read_only=True)

    # Escribe variante usando ID
    variante_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductoVariante.objects.filter(activo=True, stock__gt=0),
        source="variante",
        write_only=True,
    )

    class Meta:
        model = DetallePedido
        fields = [
            "id",
            "pedido",
            "variante",
            "variante_id",
            "cantidad",
            "precio_unitario",
            "subtotal",
        ]
        read_only_fields = ["id", "pedido", "precio_unitario", "subtotal"]

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad debe ser mayor a cero.")
        return value


# ===========================
#   PEDIDO
# ===========================
class PedidoSerializer(serializers.ModelSerializer):
    # Nombres de cliente y empleado
    cliente_nombre = serializers.CharField(
        source="cliente.username", read_only=True)
    empleado_nombre = serializers.CharField(
        source="empleado.username", read_only=True)

    # Estado
    estado = EstadoSerializer(read_only=True)
    estado_id = serializers.PrimaryKeyRelatedField(
        queryset=EstadoPedido.objects.all(),
        source="estado",
        write_only=True
    )

    # Método de pago
    metodo_pago = MetodoPagoSerializer(read_only=True)
    metodo_pago_id = serializers.PrimaryKeyRelatedField(
        queryset=MetodoPago.objects.all(),
        source="metodo_pago",
        write_only=True,
    )

    # 🔥 MOSTRAR DETALLES (funciona por related_name="detalles")
    detalles = DetallePedidoSerializer(many=True, read_only=True)

    tipo = serializers.ChoiceField(
        choices=Pedido.TIPO_CHOICES, default="interno")

    class Meta:
        model = Pedido
        fields = [
            "id",
            "cliente",
            "cliente_nombre",
            "empleado",
            "empleado_nombre",
            "mesa",
            "notas",
            "fecha_pedido",
            "estado",
            "estado_id",
            "metodo_pago",
            "metodo_pago_id",
            "total",
            "detalles",
            "tipo",
        ]
        read_only_fields = ["fecha_pedido", "total"]

    # Validaciones globales
    def validate(self, data):
        if self.instance is None:  # Creación
            if data.get("estado") is None:
                raise serializers.ValidationError(
                    {"estado_id": "Este campo es obligatorio."})
            if data.get("metodo_pago") is None:
                raise serializers.ValidationError(
                    {"metodo_pago_id": "Este campo es obligatorio."})

        mesa = data.get("mesa")
        if mesa is not None and not isinstance(mesa, int):
            raise serializers.ValidationError(
                {"mesa": "Debe ser un número o nulo."})

        return data

    # Evitar cambiar estado finalizado
    def validate_estado(self, value):
        if self.instance and self.instance.estado.nombre in ["Entregado", "Cancelado"]:
            raise serializers.ValidationError(
                "No se puede cambiar el estado de un pedido finalizado.")
        return value

    # Crear pedido
    def create(self, validated_data):
        request = self.context.get("request")

        # Si no viene cliente/empleado, usar el usuario logueado
        if request:
            validated_data.setdefault("cliente", request.user)
            validated_data.setdefault("empleado", request.user)

        return super().create(validated_data)
