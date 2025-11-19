from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()

# ---------- VALIDACIONES AUXILIARES ----------


def validar_fecha_en_rango(credito, fecha_op=None):
    if fecha_op is None:
        fecha_op = timezone.now()
    if fecha_op < credito.fecha_inicio:
        raise ValidationError(
            "No se pueden realizar operaciones antes de la fecha de inicio del crédito.")
    if credito.fecha_fin and fecha_op > credito.fecha_fin:
        raise ValidationError(
            "No se pueden realizar operaciones después de la fecha de fin del crédito.")


def validar_activar(credito, usuario):
    if credito.estado and credito.estado.nombre == "Suspendido" and not usuario.is_staff:
        raise ValidationError(
            "Solo un administrador puede re-activar un crédito suspendido.")


def validar_pago_con_estado(credito):
    if credito.estado and credito.estado.nombre == "Pagado":
        raise ValidationError("El crédito ya está pagado.")


def validar_cambio_a_pagado(credito):
    if credito.estado and credito.estado.nombre == "Pagado" and credito.deuda > 0:
        raise ValidationError(
            "No se puede marcar como Pagado mientras la deuda sea superior a 0.")


# ---------- MODELOS EXISTENTES ----------
class EstadoCredito(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class TipoMovimiento(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Credito(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="creditos",
        limit_choices_to={'rol': 'CLIENTE'}
    )
    limite = models.DecimalField(max_digits=10, decimal_places=2)
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.ForeignKey(
        EstadoCredito, on_delete=models.SET_NULL, null=True, related_name="creditos"
    )
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Crédito de {self.cliente} - Saldo: {self.saldo}/{self.limite}"

    @property
    def deuda(self):
        return self.limite - self.saldo

    def clean(self):
        super().clean()
        if self.pk:
            validar_cambio_a_pagado(self)
        if self.fecha_fin and timezone.now() > self.fecha_fin:
            if self.estado and self.estado.nombre == "Activo":
                raise ValidationError(
                    "No se puede re-activar un crédito vencido.")

    def save(self, *args, **kwargs):
        if not self.pk:
            self.saldo = self.limite
        self.full_clean()
        super().save(*args, **kwargs)

    def actualizar_estado(self):
        if self.saldo == self.limite:
            estado, _ = EstadoCredito.objects.get_or_create(nombre="Pagado")
        elif self.saldo > 0:
            estado, _ = EstadoCredito.objects.get_or_create(nombre="Activo")
        else:
            estado, _ = EstadoCredito.objects.get_or_create(
                nombre="Suspendido")
        self.estado = estado
        self.save(update_fields=["estado"])

    def consumir(self, monto, detalle="", pedido=None):
        if monto <= 0:
            raise ValueError("El monto de consumo debe ser mayor a 0.")
        if monto > self.saldo:
            raise ValueError("Saldo insuficiente.")
        validar_fecha_en_rango(self)
        tipo_consumo, _ = TipoMovimiento.objects.get_or_create(
            nombre="Consumo")
        MovimientoCredito.objects.create(
            credito=self,
            tipo=tipo_consumo,
            monto=monto,
            detalle=detalle,
            pedido=pedido
        )
        self.actualizar_estado()

    def pagar(self, monto, detalle=""):
        if monto <= 0:
            raise ValueError("El monto de pago debe ser mayor a 0.")
        validar_pago_con_estado(self)
        deuda = self.limite - self.saldo
        if deuda <= 0:
            raise ValueError("Sin deuda pendiente.")
        if monto > deuda:
            raise ValueError("El pago excede la deuda.")
        validar_fecha_en_rango(self)
        tipo_pago, _ = TipoMovimiento.objects.get_or_create(nombre="Pago")
        MovimientoCredito.objects.create(
            credito=self,
            tipo=tipo_pago,
            monto=monto,
            detalle=detalle
        )
        self.actualizar_estado()


class MovimientoCredito(models.Model):
    credito = models.ForeignKey(
        Credito, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.ForeignKey(
        TipoMovimiento, on_delete=models.SET_NULL, null=True, related_name="movimientos")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(default=timezone.now)
    detalle = models.TextField(blank=True, null=True)
    pedido = models.ForeignKey(
        "pedidos.Pedido",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_credito"
    )

    class Meta:
        ordering = ["-fecha"]

    def clean(self):
        super().clean()
        if self.monto is None or self.monto <= 0:
            raise ValidationError("Monto debe ser mayor a 0.")
        if not self.tipo:
            raise ValidationError("Tipo de movimiento obligatorio.")
        validar_fecha_en_rango(self.credito, self.fecha)
        if self.tipo.nombre == "Consumo":
            if self.monto > self.credito.saldo:
                raise ValidationError("Saldo insuficiente.")
        elif self.tipo.nombre == "Pago":
            validar_pago_con_estado(self.credito)
            deuda = self.credito.limite - self.credito.saldo
            if self.monto > deuda:
                raise ValidationError("El pago excede la deuda pendiente.")

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            if self.tipo.nombre == "Consumo":
                self.credito.saldo -= self.monto
            elif self.tipo.nombre == "Pago":
                self.credito.saldo += self.monto
            self.credito.save(update_fields=["saldo"])
            super().save(*args, **kwargs)
            self.credito.actualizar_estado()
            AuditoriaCredito.objects.create(
                credito=self.credito,
                usuario=self.credito.cliente,
                pedido=self.pedido,
                accion=f"{self.tipo.nombre} de crédito",
                detalle=f"Monto: {self.monto}",
            )

    def __str__(self):
        return f"{self.tipo} - {self.monto} ({self.fecha.date()})"


class AuditoriaCredito(models.Model):
    credito = models.ForeignKey(
        "finanzas.Credito", on_delete=models.CASCADE, related_name="auditorias")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    pedido = models.ForeignKey(
        "pedidos.Pedido",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditorias_credito"
    )
    accion = models.CharField(max_length=100)
    fecha = models.DateTimeField(default=timezone.now)
    detalle = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Auditoría - {self.accion} ({self.fecha.date()})"


# ---------- MODELOS DE ACREDITACIÓN ----------
class EstadoSolicitud(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class SolicitudAcreditacion(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="solicitudes")
    monto_solicitado = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.ForeignKey(
        EstadoSolicitud, on_delete=models.SET_NULL, null=True)
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    observaciones_staff = models.TextField(blank=True, null=True)
    fecha_rechazo = models.DateTimeField(
        null=True, blank=True,
        help_text="Fecha en que fue rechazada (bloqueo 15 días)"
    )
    credito_resultante = models.OneToOneField(
        Credito,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitud_origen"
    )

    def __str__(self):
        return f"Solicitud de {self.cliente} - ${self.monto_solicitado} ({self.estado})"

    def clean(self):
        if self.estado and self.estado.nombre == "Aprobado" and not self.credito_resultante:
            raise ValidationError(
                "Una solicitud aprobada debe tener un crédito asociado.")
