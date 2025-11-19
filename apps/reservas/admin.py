from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Ubicacion, Mesa, EstadoReserva, Reserva
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero', 'capacidad',
                    'ubicacion', 'disponible', 'activo')
    search_fields = ('numero', 'capacidad', 'ubicacion__nombre')
    list_filter = ('ubicacion', 'disponible', 'activo')
    fields = ('numero', 'capacidad', 'ubicacion', 'disponible', 'activo')


@admin.register(EstadoReserva)
class EstadoReservaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre',)
    search_fields = ('nombre',)
    fields = ('nombre',)


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mesa', 'fecha', 'hora_inicio',
                    'hora_fin', 'numero_personas', 'estados_coloreado', 'notas')
    readonly_fields = ('usuario', 'hora_fin', 'creada_en')
    list_filter = ('estado', 'fecha', 'mesa__ubicacion',)
    search_fields = ('usuario__username', 'mesa__numero')
    date_hierarchy = 'fecha'
    ordering = ('-fecha', '-hora_inicio')

    fieldsets = (
        (None, {
            'fields': ('usuario', 'mesa', 'fecha', 'hora_inicio', 'hora_fin', 'numero_personas', 'estado', 'notas')
        }),
        ('Auditoría', {
            'fields': ('creada_en',),
            'classes': ('collapse',)
        }),
    )

    def estados_coloreado(self, obj):
        color = ""
        if obj.estado.nombre == "Pendiente":
            color = "#ffa200"
        elif obj.estado.nombre == "Confirmada":
            color = "#00ff3c"
        elif obj.estado.nombre == "Cancelada":
            color = "#ea0000"
        return format_html(
            '<span style="background-color:{};color:white;padding:2px 8px;border-radius:4px;">{}</span>',
            color,
            obj.estado.nombre
        )
    estados_coloreado.short_description = "Estado"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "usuario":
            kwargs["queryset"] = User.objects.filter(rol='CLIENTE')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado.nombre in ["Confirmada", "Cancelada"]:
            return ["usuario", "mesa", "fecha", "hora_inicio", "hora_fin", "numero_personas", "estado", "notas", "creada_en"]
        return ["hora_fin", "creada_en"]

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions['marcar_confirmada'] = (
            self.marcar_confirmada, 'marcar_confirmada', "Marcar como Confirmada")
        actions['marcar_cancelada'] = (
            self.marcar_cancelada, 'marcar_cancelada', "Marcar como Cancelada")
        return actions

    @admin.action(description="Marcar seleccionadas como Confirmadas")
    def marcar_confirmada(self, request, queryset):
        confirmadas = queryset.update(estado_id=2)
        self.message_user(request, f"{confirmadas} reservas confirmadas.")

    @admin.action(description="Marcar seleccionadas como Canceladas")
    def marcar_cancelada(self, request, queryset):
        canceladas = queryset.update(estado_id=3)
        self.message_user(request, f"{canceladas} reservas canceladas.")

    # ✅ Eliminado el filtro de fecha futura: mostramos TODAS las reservas
    def get_queryset(self, request):
        return super().get_queryset(request)

    def franja_horaria(self, obj):
        return f"{obj.hora_inicio} - {obj.hora_fin}"
    franja_horaria.short_description = "Franja"
