from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone


# ---------- Estado ----------
class EstadoPedido(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    orden = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


# ---------- Método de Pago ----------
class MetodoPago(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


# ---------- Pedido ----------
class Pedido(models.Model):
    TIPO_CHOICES = [("interno", "Interno"), ("externo", "Externo")]

    cliente = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_como_cliente",
        limit_choices_to={'rol': 'CLIENTE'}
    )
    empleado = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_creados",
        limit_choices_to={'rol': 'MESERO'}
    )

    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.ForeignKey(EstadoPedido, on_delete=models.PROTECT)
    tipo = models.CharField(
        max_length=20, choices=TIPO_CHOICES, default="interno")
    mesa = models.PositiveIntegerField(null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT)
    notas = models.TextField(blank=True, null=True)
    cancelado = models.BooleanField(default=False)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.fecha_pedido.strftime('%Y-%m-%d %H:%M')}"

    def calcular_total(self):
        return sum(detalle.subtotal for detalle in self.detalles.all())

    # ---------- LÓGICA DE ESTADOS Y STOCK ----------
    @transaction.atomic
    def confirmar(self):
        if self.cancelado:
            raise ValidationError("Pedido ya cancelado.")

        for detalle in self.detalles.all():
            detalle.variante.bloquear(detalle.cantidad)

        self.estado, _ = EstadoPedido.objects.get_or_create(nombre="Pendiente")
        self.save(update_fields=['estado'])

    @transaction.atomic
    def entregar(self):
        if self.cancelado:
            raise ValidationError("Pedido ya cancelado.")

        for detalle in self.detalles.all():
            detalle.variante.desbloquear(detalle.cantidad)
            detalle.variante.descontar(detalle.cantidad)

        if self.metodo_pago.nombre.lower() == "credito" and self.cliente:
            credito = self.cliente.creditos.filter(
                estado__nombre="Activo").first()
            if not credito:
                raise ValidationError(
                    "El cliente no tiene un crédito activo aprobado.")
            credito.consumir(
                self.total, detalle=f"Pedido #{self.id}", pedido=self)

        self.estado, _ = EstadoPedido.objects.get_or_create(nombre="Entregado")
        self.save(update_fields=['estado'])

    @transaction.atomic
    def cancelar(self):
        if self.cancelado:
            raise ValidationError("Pedido ya cancelado.")

        for detalle in self.detalles.all():
            detalle.variante.desbloquear(detalle.cantidad)

        self.cancelado = True
        self.fecha_cancelacion = timezone.now()
        self.estado, _ = EstadoPedido.objects.get_or_create(nombre="Cancelado")
        self.save(update_fields=['cancelado', 'fecha_cancelacion', 'estado'])

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total_calculado = self.calcular_total()
        if self.total != total_calculado:
            self.total = total_calculado
            super().save(update_fields=['total'])


# ---------- Detalle ----------
class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles"   # ⭐ CORREGIDO
    )
    variante = models.ForeignKey(
        "inventario.ProductoVariante",
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.cantidad} x {self.variante} (Pedido #{self.pedido.id})"

    def calcular_subtotal(self):
        return self.cantidad * self.precio_unitario

    def clean(self):
        if self.cantidad < 1:
            raise ValidationError("La cantidad debe ser al menos 1.")
        if self.variante and self.pk is None:
            if self.cantidad > self.variante.stock_disponible:
                raise ValidationError(
                    "No hay stock disponible para esta variante.")

    @transaction.atomic
    def save(self, *args, **kwargs):
        if not self.variante:
            raise ValidationError("Debe seleccionar una variante válida.")
        if not self.precio_unitario:
            self.precio_unitario = self.variante.precio

        self.subtotal = self.calcular_subtotal()

        if self.pedido.estado.nombre == "Entregado":
            self.variante.desbloquear(self.cantidad)
            self.variante.descontar(self.cantidad)

        estados_bloquean = ["Pendiente", "En cocina", "Listo"]
        if self.pedido.estado.nombre in estados_bloquean:
            self.variante.bloquear(self.cantidad)

        super().save(*args, **kwargs)
        self.pedido.save()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.pedido.save()
