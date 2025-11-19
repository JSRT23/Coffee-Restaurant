from decimal import Decimal
from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.finanzas.models import Credito
from apps.inventario.models import ProductoVariante
from .models import Pedido, EstadoPedido, MetodoPago, DetallePedido


# ---------- Detalle Inline ----------
class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ('subtotal', 'variante_info')

    def get_fields(self, request, obj=None):
        if obj is None:
            return ('variante', 'cantidad', 'subtotal')
        # ❌ Cuando el pedido ya existe, no se permite editar cantidad
        return ('variante_info', 'cantidad', 'subtotal')

    def get_readonly_fields(self, request, obj=None):
        # 🔒 Si el pedido ya existe, la cantidad no se puede editar
        if obj is not None:
            return ('variante_info', 'cantidad', 'subtotal')
        return self.readonly_fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "variante":
            kwargs["queryset"] = ProductoVariante.objects.filter(
                activo=True, stock__gt=0)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def variante_info(self, obj):
        if obj.variante:
            return f"{obj.variante.producto.nombre} - {obj.variante.nombre_variante}"
        return "-"
    variante_info.short_description = "Variante"

    def has_add_permission(self, request, obj=None):
        if obj and obj.estado.nombre in ["Entregado", "Cancelado"]:
            return False
        return super().has_add_permission(request, obj)


# ---------- Form personalizado para Pedido ----------
class PedidoAdminForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = "__all__"

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def _calcular_total_desde_post(self):
        total = Decimal("0")
        prefix = "detallepedido_set"
        try:
            total_forms = int(self.request.POST.get(
                f"{prefix}-TOTAL_FORMS", 0))
        except Exception:
            total_forms = 0

        for i in range(total_forms):
            if self.request.POST.get(f"{prefix}-{i}-DELETE"):
                continue

            var_id = self.request.POST.get(f"{prefix}-{i}-variante")
            qty = self.request.POST.get(f"{prefix}-{i}-cantidad", "0") or "0"

            try:
                cantidad = Decimal(qty)
            except Exception:
                cantidad = Decimal("0")

            price = Decimal("0")
            if var_id:
                try:
                    var = ProductoVariante.objects.get(pk=int(var_id))
                    price = var.precio
                except Exception:
                    price = Decimal(self.request.POST.get(
                        f"{prefix}-{i}-precio_unitario", "0") or "0")
            else:
                price = Decimal(self.request.POST.get(
                    f"{prefix}-{i}-precio_unitario", "0") or "0")

            total += price * cantidad

        return total

    def clean(self):
        cleaned = super().clean()
        metodo = cleaned.get("metodo_pago")
        cliente = cleaned.get("cliente")

        if metodo and metodo.nombre and metodo.nombre.lower().strip() == "credito":
            if not cliente:
                self.add_error(
                    "cliente", "Debe asignar un cliente para pagar con crédito.")
                raise forms.ValidationError("Error de validación en crédito.")

            credito = Credito.objects.filter(
                cliente=cliente, estado__nombre="Activo").first()
            if not credito:
                self.add_error(
                    "cliente", "El cliente no tiene un crédito activo aprobado.")
                raise forms.ValidationError("Error de validación en crédito.")

            if getattr(self, "request", None):
                total = self._calcular_total_desde_post()
            else:
                try:
                    total = self.instance.calcular_total()
                except Exception:
                    total = Decimal(self.instance.total or 0)

            if total > credito.saldo:
                self.add_error(
                    "cliente", f"Saldo insuficiente en crédito. Saldo: {credito.saldo}, Total: {total}.")
                raise forms.ValidationError(
                    "El total del pedido supera el saldo disponible en el crédito.")

        return cleaned


# ---------- Pedido Admin ----------
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    form = PedidoAdminForm
    inlines = [DetallePedidoInline]
    list_display = ("id", "cliente", "empleado", "estado_coloreado",
                    "total", "fecha_pedido", "tipo", "mesa")
    list_filter = ("estado", "tipo", "metodo_pago", "fecha_pedido")
    readonly_fields = ("fecha_pedido", "total",
                       "cancelado", "fecha_cancelacion")
    search_fields = ("cliente__username", "empleado__username", "mesa")
    ordering = ("-fecha_pedido",)
    actions = ["marcar_en_cocina", "marcar_listo",
               "marcar_entregado", "cancelar_pedidos"]

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}

        if object_id:
            pedido = Pedido.objects.filter(pk=object_id).first()
            if pedido and pedido.estado.nombre in ["Entregado", "Cancelado"]:
                # Si está entregado o cancelado, solo mostrar "Cerrar" y "Eliminar"
                extra_context["show_save"] = False
                extra_context["show_save_and_continue"] = False
                extra_context["show_save_and_add_another"] = False
                extra_context["show_delete"] = True
                extra_context["show_close"] = True

        return super().changeform_view(request, object_id, form_url, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        class RequestAwareForm(Form):
            def __init__(self_inner, *args, **inner_kwargs):
                inner_kwargs.setdefault("request", request)
                super().__init__(*args, **inner_kwargs)
        return RequestAwareForm

    def estado_coloreado(self, obj):
        colores = {
            "Pendiente": "#fff700",
            "En cocina": "#007bff",
            "Listo": "#00ff3c",
            "Entregado": "#23314d",
            "Cancelado": "#ff0000",
        }
        color = colores.get(obj.estado.nombre, "#ccc")
        return format_html('<span style="background-color:{};padding:4px 8px;border-radius:4px;">{}</span>',
                           color, obj.estado.nombre)
    estado_coloreado.short_description = "Estado"

    @transaction.atomic
    def marcar_en_cocina(self, request, queryset):
        estado_cocina, _ = EstadoPedido.objects.get_or_create(
            nombre="En cocina")
        confirmados = 0
        for pedido in queryset:
            try:
                pedido.confirmar()
                pedido.estado = estado_cocina
                pedido.save(update_fields=["estado"])
                confirmados += 1
            except ValidationError as e:
                self.message_user(
                    request, f"Pedido {pedido.id}: {e}", messages.ERROR)
        if confirmados:
            self.message_user(
                request, f"{confirmados} pedidos pasaron a En cocina.", messages.SUCCESS)
    marcar_en_cocina.short_description = "🍳 Pasar a En cocina (descontar stock)"

    def marcar_listo(self, request, queryset):
        estado_listo, _ = EstadoPedido.objects.get_or_create(nombre="Listo")
        actualizados = queryset.update(estado=estado_listo)
        if actualizados:
            self.message_user(
                request, f"{actualizados} pedidos marcados como Listo.", messages.SUCCESS)
    marcar_listo.short_description = "🔔 Marcar como Listo"

    @transaction.atomic
    def marcar_entregado(self, request, queryset):
        estado_entregado, _ = EstadoPedido.objects.get_or_create(
            nombre="Entregado")
        entregados = 0
        for pedido in queryset:
            try:
                if pedido.estado.nombre not in ["En cocina", "Entregado"]:
                    pedido.confirmar()
                pedido.entregar()
                entregados += 1
            except ValidationError as e:
                self.message_user(
                    request, f"Pedido {pedido.id}: {e}", messages.ERROR)
        if entregados:
            self.message_user(
                request, f"Se entregaron {entregados} pedidos.", messages.SUCCESS)
    marcar_entregado.short_description = "✔ Marcar como Entregado"

    @transaction.atomic
    def cancelar_pedidos(self, request, queryset):
        estado_cancelado, _ = EstadoPedido.objects.get_or_create(
            nombre="Cancelado")
        cancelados = 0
        for pedido in queryset:
            try:
                pedido.cancelar()
                cancelados += 1
            except ValidationError as e:
                self.message_user(
                    request, f"Pedido {pedido.id}: {e}", messages.ERROR)
        if cancelados:
            self.message_user(
                request, f"Se cancelaron {cancelados} pedidos.", messages.WARNING)
    cancelar_pedidos.short_description = "❌ Cancelar pedidos seleccionados"

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and obj.estado.nombre in ["Entregado", "Cancelado"]:
            for field in self.model._meta.fields:
                readonly.append(field.name)
        return readonly

    def has_change_permission(self, request, obj=None):
        if obj and obj.estado.nombre in ["Entregado", "Cancelado"]:
            return request.method in ["GET", "HEAD"]
        return super().has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if change:
            old = Pedido.objects.get(pk=obj.pk)
            if old.estado.nombre != "Entregado" and obj.estado.nombre == "Entregado":
                try:
                    obj.entregar()
                except ValidationError as e:
                    self.message_user(request, str(e), level=messages.ERROR)
                    return
            elif old.estado.nombre != "Cancelado" and obj.estado.nombre == "Cancelado":
                try:
                    obj.cancelar()
                except ValidationError as e:
                    self.message_user(request, str(e), level=messages.ERROR)
                    return
        super().save_model(request, obj, form, change)


# ---------- Estado ----------
@admin.register(EstadoPedido)
class EstadoPedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion", "orden", "activo")
    ordering = ("orden",)


# ---------- Método de Pago ----------
@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion", "activo")
