from django.db import models
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import json

User = get_user_model()

# ---------- 1. Canal ----------


class Canal(models.Model):
    # email, sms, whatsapp, push
    nombre = models.CharField(max_length=20, unique=True)
    descripcion = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.descripcion})"

# ---------- 2. Plantilla ----------


class Plantilla(models.Model):
    EVENTOS = [
        ('usuario_registrado', 'Usuario registrado'),
        ('pedido_creado', 'Pedido creado'),
        ('pedido_entregado', 'Pedido entregado'),
        ('pedido_cancelado', 'Pedido cancelado'),
        ('reserva_creada', 'Reserva creada'),
        ('reserva_confirmada', 'Reserva confirmada'),
        ('reserva_cancelada', 'Reserva cancelada'),
        ('credito_aprobado', 'Crédito aprobado'),
        ('consumo_credito_realizado', 'Consumo de crédito realizado'),
        ('pago_credito_confirmado', 'Pago de crédito confirmado'),
        ('credito_suspendido', 'Crédito suspendido'),
        ('credito_pagado_total', 'Crédito pagado total'),
        ('stock_bajo_alcanzado', 'Stock bajo alcanzado'),
        ('producto_agotado', 'Producto agotado'),
    ]

    evento = models.CharField(max_length=50, choices=EVENTOS)
    canal = models.ForeignKey(Canal, on_delete=models.CASCADE)
    asunto = models.CharField(max_length=255, blank=True, null=True)
    cuerpo_txt = models.TextField()
    cuerpo_html = models.TextField(blank=True, null=True)
    idioma = models.CharField(max_length=10, default='es')
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.evento} → {self.canal} ({self.idioma})"

    class Meta:
        unique_together = ('evento', 'canal', 'idioma')

# ---------- 3. PreferenciaCanal ----------


class PreferenciaCanal(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    evento = models.CharField(max_length=50, choices=Plantilla.EVENTOS)
    canal = models.ForeignKey(Canal, on_delete=models.CASCADE)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario} | {self.evento} → {self.canal}"

    class Meta:
        unique_together = ('usuario', 'evento')

# ---------- 4. Notificación ----------


class Notificacion(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
        ('reintentando', 'Reintentando'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    evento = models.CharField(max_length=50, choices=Plantilla.EVENTOS)
    plantilla = models.ForeignKey(Plantilla, on_delete=models.CASCADE)
    destinatario = models.CharField(max_length=255)  # email o teléfono
    contexto_json = models.JSONField(default=dict)
    estado = models.CharField(
        max_length=20, choices=ESTADOS, default='pendiente')
    intento = models.PositiveSmallIntegerField(default=0)
    max_intentos = models.PositiveSmallIntegerField(default=3)
    prox_reintento = models.DateTimeField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    enviado_en = models.DateTimeField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario} | {self.evento} ({self.estado})"

# ---------- 5. NotificacionLeida (opcional) ----------


class NotificacionLeida(models.Model):
    notificacion = models.OneToOneField(Notificacion, on_delete=models.CASCADE)
    leida = models.BooleanField(default=False)
    leida_en = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Leída: {self.leida} | {self.notificacion}"
