from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import (
    TipoMovimiento, EstadoCredito, Credito, AuditoriaCredito,
    EstadoSolicitud, SolicitudAcreditacion
)
from django.utils.html import format_html
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()


class ClientePorRolModelChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs["queryset"] = User.objects.filter(
            rol='CLIENTE').order_by("username")
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        return f"{obj.username} ({obj.email})"


class CreditoAdminForm(forms.ModelForm):
    cliente = ClientePorRolModelChoiceField()

    class Meta:
        model = Credito
        fields = "__all__"


@admin.register(TipoMovimiento)
class TipoMovimientoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion")
    search_fields = ("nombre",)


@admin.register(EstadoCredito)
class EstadoCreditoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion")
    search_fields = ("nombre",)


@admin.register(Credito)
class CreditoAdmin(admin.ModelAdmin):
    form = CreditoAdminForm
    list_display = (
        "id", "cliente", "limite", "saldo", "estado_badge", "fecha_inicio", "deuda_coloreada",
    )
    list_filter = ("estado", "fecha_inicio")
    search_fields = ("cliente__username",)
    ordering = ("-fecha_inicio",)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ['saldo']
        return [f.name for f in self.model._meta.fields if f.name != "estado"]

    def save_model(self, request, obj, form, change):
        if change:
            if obj.estado and obj.estado.nombre == "Suspendido" and not request.user.is_staff:
                from django.contrib import messages
                messages.set_level(request, messages.ERROR)
                messages.error(
                    request, "Solo un administrador puede re-activar un crédito suspendido.")
                return
        if obj.estado and obj.estado.nombre == "Pagado" and obj.deuda > 0:
            from django.contrib import messages
            messages.set_level(request, messages.ERROR)
            messages.error(
                request, "No se puede marcar como Pagado mientras la deuda sea superior a 0.")
            return
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("cliente", "estado")

    def estado_badge(self, obj):
        color_map = {"Pagado": "#00ff00",
                     "Activo": "#00f7ffde", "Suspendido": "#ff0000"}
        color = color_map.get(obj.estado.nombre, "#cccccc")
        return format_html(
            '<span style="background-color:{};padding:2px 8px;border-radius:4px;">{}</span>',
            color, obj.estado.nombre,
        )
    estado_badge.short_description = "Estado"

    def deuda_coloreada(self, obj):
        deuda = obj.deuda
        color = "red" if deuda > 0 else "green"
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>', color, f"${deuda:,.0f}"
        )
    deuda_coloreada.short_description = "Deuda"


@admin.register(AuditoriaCredito)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "accion", "fecha",
                    "pedido", "detalle_pedido")
    list_filter = ("fecha",)
    search_fields = ("usuario__username", "accion")
    ordering = ("-fecha",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("usuario", "pedido").prefetch_related("pedido__detallepedido_set")

    def detalle_pedido(self, obj):
        if not obj.pedido:
            return "—"
        detalles = obj.pedido.detallepedido_set.all()
        if not detalles:
            return "Sin productos"
        return format_html("<br>".join(
            [f"{d.cantidad}x {d.variante.nombre_variante} - ${d.subtotal}" for d in detalles]
        ))
    detalle_pedido.short_description = "Productos del Pedido"


@admin.register(EstadoSolicitud)
class EstadoSolicitudAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion")


@admin.register(SolicitudAcreditacion)
class SolicitudAcreditacionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "cliente", "monto_solicitado", "estado",
        "fecha_solicitud", "fecha_respuesta", "credito_resultante"
    )
    list_filter = ("estado", "fecha_solicitud")
    search_fields = ("cliente__username",)
    readonly_fields = ("fecha_solicitud", "credito_resultante")
    actions = ["aprobar_seleccionadas"]

    def aprobar_seleccionadas(self, request, queryset):
        from django.contrib import messages
        aprobadas = 0
        for solicitud in queryset.filter(estado__nombre="En revisión"):
            solicitud.estado = EstadoSolicitud.objects.get(nombre="Aprobado")
            solicitud.fecha_respuesta = timezone.now()
            credito = Credito.objects.create(
                cliente=solicitud.cliente,
                limite=solicitud.monto_solicitado,
                estado=EstadoCredito.objects.get(nombre="Activo")
            )
            solicitud.credito_resultante = credito
            solicitud.save()
            aprobadas += 1
        if aprobadas:
            messages.success(
                request, f"{aprobadas} solicitudes aprobadas y créditos creados.")
        else:
            messages.warning(
                request, "No hay solicitudes pendientes seleccionadas.")
    aprobar_seleccionadas.short_description = "Aprobar solicitudes seleccionadas"
