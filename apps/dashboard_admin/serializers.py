from rest_framework import serializers


class DiaVentasSerializer(serializers.Serializer):
    fecha_dia = serializers.DateField()
    total_dia = serializers.DecimalField(max_digits=12, decimal_places=2)


class DetalleVentasDiaSerializer(serializers.Serializer):
    fecha = serializers.DateField()
    total_general = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_efectivo = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_transferencia = serializers.DecimalField(
        max_digits=12, decimal_places=2)
    cantidad_total_productos = serializers.IntegerField()
    categorias = serializers.JSONField()


class ProductoTopSerializer(serializers.Serializer):
    variante__producto__nombre = serializers.CharField()
    variante__nombre_variante = serializers.CharField(allow_null=True)
    total_vendido = serializers.IntegerField()


class ClienteTopSerializer(serializers.Serializer):
    cliente__username = serializers.CharField()
    total_pedidos = serializers.IntegerField()
    total_gastado = serializers.DecimalField(max_digits=12, decimal_places=2)


class KPIsGeneralesSerializer(serializers.Serializer):
    total_ventas_mes = serializers.DecimalField(
        max_digits=12, decimal_places=2)
    total_ventas_semana = serializers.DecimalField(
        max_digits=12, decimal_places=2)
    ticket_promedio = serializers.FloatField()

    producto_mas_vendido = ProductoTopSerializer(allow_null=True)
    cliente_mas_frecuente = ClienteTopSerializer(allow_null=True)
