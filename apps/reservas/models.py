from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import uuid

User = get_user_model()


class Ubicacion(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Mesa(models.Model):
    numero = models.PositiveIntegerField(unique=True)
    capacidad = models.PositiveIntegerField()
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT)
    lugar = models.CharField(max_length=50, blank=True, null=True)
    disponible = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"Mesa {self.numero} - Capacidad {self.capacidad} - {'Disponible' if self.disponible else 'No disponible'}"


class EstadoReserva(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


class Reserva(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField(editable=False)
    numero_personas = models.PositiveIntegerField()
    creada_en = models.DateTimeField(auto_now_add=True)
    estado = models.ForeignKey(EstadoReserva, on_delete=models.PROTECT)
    notas = models.TextField(blank=True, null=True)
    codigo_confirmacion = models.CharField(
        max_length=6, unique=True, editable=False, blank=True, null=True)

    class Meta:
        unique_together = ('mesa', 'fecha', 'hora_inicio')

    def save(self, *args, **kwargs):
        # Calcular hora_fin
        self.hora_fin = (datetime.combine(datetime.today(),
                         self.hora_inicio) + timedelta(minutes=30)).time()

        # Generar código único
        if not self.codigo_confirmacion:
            self.codigo_confirmacion = str(uuid.uuid4().hex[:6]).upper()

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        # Validar cruce de franjas
        if Reserva.objects.filter(
            mesa=self.mesa,
            fecha=self.fecha,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio
        ).exclude(id=self.id).exists():
            raise ValidationError(
                "La franja horaria se cruza con otra reserva existente.")
