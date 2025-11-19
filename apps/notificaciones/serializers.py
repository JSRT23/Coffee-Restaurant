from rest_framework import serializers
from .models import Notificacion, NotificacionLeida


class NotificacionSerializer(serializers.ModelSerializer):
    canal = serializers.CharField(
        source='plantilla.canal.nombre', read_only=True)
    leida = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = ['id', 'evento', 'canal',
                  'estado', 'intento', 'created', 'leida']

    def get_leida(self, obj):
        return getattr(obj, 'notificacionleida', None) and obj.notificacionleida.leida


class MarcarLeidaSerializer(serializers.Serializer):
    pass  # solo para validar que el body esté vacío
