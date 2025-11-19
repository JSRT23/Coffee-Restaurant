from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Ubicacion, Mesa, EstadoReserva, Reserva


class UbicacionSerializer(serializers.ModelSerializer):
    """Serializa sedes/ubicaciones de mesas."""

    class Meta:
        model = Ubicacion
        fields = ['id', 'nombre', 'descripcion']


class MesaSerializer(serializers.ModelSerializer):
    """Serializa mesas e incluye la sede en modo solo lectura."""

    ubicacion = UbicacionSerializer(read_only=True)

    class Meta:
        model = Mesa
        fields = ['id', 'numero', 'capacidad',
                  'ubicacion', 'disponible', 'activo']


class EstadoReservaSerializer(serializers.ModelSerializer):
    """Serializa el catálogo de estados de reserva."""

    class Meta:
        model = EstadoReserva
        fields = ['id', 'nombre']


class ReservaSerializer(serializers.ModelSerializer):
    """Serializer normal para crear/actualizar reservas."""

    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    hora_fin = serializers.TimeField(read_only=True)

    class Meta:
        model = Reserva
        fields = ['id', 'usuario', 'mesa', 'fecha', 'hora_inicio',
                  'hora_fin', 'numero_personas', 'estado', 'notas']

    def validate(self, data):
        mesa = data['mesa']
        numero_personas = data['numero_personas']
        fecha = data['fecha']
        hora_inicio = data['hora_inicio']

        # --- validación de hora mínima ---
        ahora = timezone.now()
        fecha_hora_reserva = timezone.make_aware(
            datetime.combine(fecha, hora_inicio)
        )

        # Mínimo: dentro de 1 hora
        minimo_permitido = ahora + timedelta(hours=1)

        if fecha_hora_reserva < minimo_permitido:
            raise serializers.ValidationError(
                "Las reservas deben realizarse al menos con 1 hora de anticipación."
            )
        # --- fin validación hora mínima ---

        # Capacidad
        if numero_personas > mesa.capacidad:
            raise serializers.ValidationError(
                f"La mesa {mesa.numero} solo admite {mesa.capacidad} personas."
            )

        # Mesa activa y disponible
        if not mesa.activo or not mesa.disponible:
            raise serializers.ValidationError(
                f"La mesa {mesa.numero} no está disponible."
            )

        # Cruce de franjas
        hora_fin = (datetime.combine(datetime.today(),
                    hora_inicio) + timedelta(minutes=30)).time()
        if Reserva.objects.filter(
            mesa=mesa,
            fecha=fecha,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio
        ).exists():
            raise serializers.ValidationError(
                "La franja horaria ya está reservada."
            )

        return data


class MisReservaSerializer(serializers.ModelSerializer):
    estado = EstadoReservaSerializer(read_only=True)
    mesa = MesaSerializer(read_only=True)
    cliente_nombre = serializers.SerializerMethodField()   # ⬅ nuevo

    class Meta:
        model = Reserva
        fields = [
            'id', 'usuario', 'mesa', 'fecha', 'hora_inicio', 'hora_fin',
            'numero_personas', 'estado', 'notas', 'creada_en', 'codigo_confirmacion',
            'cliente_nombre',
        ]

    def get_cliente_nombre(self, obj):
        nombre = obj.usuario.first_name.strip()
        apellido = obj.usuario.last_name.strip()
        if nombre or apellido:
            return f"{nombre} {apellido}".strip()
        return obj.usuario.username
