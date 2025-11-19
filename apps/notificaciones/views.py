from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Notificacion, NotificacionLeida
from .serializers import NotificacionSerializer, MarcarLeidaSerializer


class MisNotificacionesView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notificacion.objects.filter(
            usuario=self.request.user
        ).select_related('plantilla__canal').order_by('-created')


class MarcarLeidaView(generics.UpdateAPIView):
    queryset = Notificacion.objects.all()
    serializer_class = MarcarLeidaSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        noti = self.get_object()
        if noti.usuario != request.user:
            return Response({"detail": "No es tu notificación"}, status=403)
        leida, _ = NotificacionLeida.objects.get_or_create(notificacion=noti)
        leida.leida = True
        leida.leida_en = timezone.now()
        leida.save()
        return Response({"detail": "Marcada como leída"})
