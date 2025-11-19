from rest_framework import serializers
from .models import (
    EstadoCredito, Credito, TipoMovimiento, MovimientoCredito,
    AuditoriaCredito, EstadoSolicitud, SolicitudAcreditacion
)


class EstadoCreditoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoCredito
        fields = "__all__"


class TipoMovimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoMovimiento
        fields = "__all__"


class CreditoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(
        source="cliente.username", read_only=True)
    estado_nombre = serializers.CharField(
        source="estado.nombre", read_only=True)

    class Meta:
        model = Credito
        fields = ["id", "cliente", "cliente_nombre", "limite", "saldo",
                  "estado", "estado_nombre", "fecha_inicio"]

    def validate_limite(self, value):
        if value <= 0:
            raise serializers.ValidationError("El límite debe ser mayor a 0.")
        return value

    def validate_saldo(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El saldo no puede ser negativo.")
        return value


class MovimientoCreditoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(
        source="credito.cliente.username", read_only=True)
    tipo_nombre = serializers.CharField(source="tipo.nombre", read_only=True)

    class Meta:
        model = MovimientoCredito
        fields = [
            "id", "credito", "cliente_nombre", "tipo", "tipo_nombre",
            "monto", "fecha", "detalle"
        ]

    def validate(self, attrs):
        monto = attrs.get("monto")
        if monto is not None and monto <= 0:
            raise serializers.ValidationError({"monto": "Debe ser mayor a 0."})
        return attrs


class AuditoriaCreditoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source="usuario.username", read_only=True)

    class Meta:
        model = AuditoriaCredito
        fields = ["id", "credito", "usuario",
                  "usuario_nombre", "accion", "fecha", "detalle"]


# ---------- ACREDITACIÓN ----------
class EstadoSolicitudSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoSolicitud
        fields = "__all__"


class SolicitudAcreditacionSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(
        source="cliente.username", read_only=True)
    estado_nombre = serializers.CharField(
        source="estado.nombre", read_only=True)

    class Meta:
        model = SolicitudAcreditacion
        fields = [
            "id", "cliente", "cliente_nombre", "monto_solicitado",
            "estado", "estado_nombre", "fecha_solicitud", "fecha_respuesta",
            "observaciones_staff", "credito_resultante"
        ]
        read_only_fields = [
            "cliente", "fecha_solicitud", "fecha_respuesta", "credito_resultante"
        ]

    def validate_monto_solicitado(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a 0.")
        return value
