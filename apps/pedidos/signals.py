from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import Pedido


@receiver(pre_save, sender=Pedido)
def validar_credito(sender, instance, **kwargs):
    if instance.metodo_pago and instance.metodo_pago.nombre.lower() == "credito":
        if not instance.cliente:
            raise ValidationError(
                "El pedido con crédito debe tener un cliente asignado.")
        credito = instance.cliente.creditos.filter(
            estado__nombre="Activo").first()
        if not credito:
            raise ValidationError(
                "El cliente no tiene un crédito activo aprobado.")
        if instance.total > credito.saldo:
            raise ValidationError(
                "El total del pedido supera el saldo disponible del crédito.")
