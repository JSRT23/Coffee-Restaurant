from django.contrib import admin, messages
from django.utils.html import format_html
from django.db import transaction
from django.shortcuts import render
from django.forms import BaseInlineFormSet
from .models import Ubicacion, Categoria, SubCategoria, Producto, ProductoVariante

# ---------- Ubicación ----------


@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

# ---------- Categoría ----------


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'estado')
    search_fields = ('nombre',)
    list_filter = ('estado',)
    ordering = ('nombre',)

# ---------- SubCategoría ----------


@admin.register(SubCategoria)
class SubCategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'categoria', 'estado')
    list_filter = ('categoria', 'estado')
    search_fields = ('nombre',)

# ---------- FormSet Inline ----------


class ProductoVarianteInlineFormSet(BaseInlineFormSet):
    def save_existing(self, form, instance, commit=True):
        obj = form.save(commit=False)
        obj.clean()
        obj.save()
        if commit:
            form.save_m2m()
        return obj

    def save_new(self, form, commit=True):
        obj = form.save(commit=False)
        obj.clean()
        obj.save()
        if commit:
            form.save_m2m()
        return obj

# ---------- Inline Variante ----------


class ProductoVarianteInline(admin.TabularInline):
    model = ProductoVariante
    extra = 1
    fields = (
        'nombre_variante', 'sku', 'codigo_barras',
        'precio', 'costo', 'stock', 'stock_minimo',
        'ubicacion', 'activo'
    )
    formset = ProductoVarianteInlineFormSet

# ---------- Producto ----------


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'subcategoria', 'activo')
    list_filter = ('subcategoria__categoria', 'subcategoria', 'activo')
    search_fields = ('nombre', 'descripcion')
    ordering = ('nombre',)
    inlines = [ProductoVarianteInline]

# ---------- Producto Variante ----------


@admin.register(ProductoVariante)
class ProductoVarianteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "producto_nombre",          # ✅ PRODUCTO PADRE
        "nombre_variante",
        "sku",
        "codigo_barras",
        "stock_disponible_colored",
        "precio",
        "costo",
        "margen",
        "stock",
        "activo",
        "stock_bloqueado",
        "ubicacion",
    )

    list_filter = (
        "producto__subcategoria__categoria",
        "producto",
        "ubicacion",
        "activo",
    )

    search_fields = (
        "sku",
        "codigo_barras",
        "nombre_variante",
        "producto__nombre",
    )

    readonly_fields = ("ultima_compra",)

    actions = [
        "activar_seleccionados",
        "desactivar_seleccionados",
        "ajustar_stock",
        "liberar_bloqueo",
    ]

    # ---------- PRODUCTO ----------
    def producto_nombre(self, obj):
        return obj.producto.nombre
    producto_nombre.short_description = "Producto"
    producto_nombre.admin_order_field = "producto__nombre"

    # ---------- STOCK VISUAL ----------
    def stock_disponible_colored(self, obj):
        disponible = obj.stock_disponible
        if disponible <= 0:
            color, texto = "red", "Agotado"
        elif obj.alerta_stock:
            color, texto = "orange", f"{disponible} (bajo)"
        else:
            color, texto = "green", f"{disponible} (disp.)"
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            color,
            texto
        )
    stock_disponible_colored.short_description = "Stock disp."

    def margen(self, obj):
        return f"{obj.margen:.1f} %" if obj.costo else "-"
    margen.short_description = "Margen"

    # ---------- ACCIONES ----------
    @transaction.atomic
    def ajustar_stock(self, request, queryset):
        if "apply" in request.POST:
            cantidad = int(request.POST["cantidad"])
            for variante in queryset:
                variante.stock += cantidad
                variante.save(update_fields=["stock"])
            self.message_user(
                request,
                f"Stock ajustado en {cantidad} unidades.",
                messages.SUCCESS
            )
            return
        return render(
            request,
            "admin/ajuste_stock_intermediate.html",
            context={"variantes": queryset}
        )
    ajustar_stock.short_description = "🔧 Ajustar stock masivamente"

    def activar_seleccionados(self, request, queryset):
        queryset.update(activo=True)
        self.message_user(request, "Variantes activadas.", messages.SUCCESS)
    activar_seleccionados.short_description = "✅ Activar seleccionados"

    def desactivar_seleccionados(self, request, queryset):
        queryset.update(activo=False)
        self.message_user(request, "Variantes desactivadas.", messages.SUCCESS)
    desactivar_seleccionados.short_description = "❌ Desactivar seleccionados"

    def liberar_bloqueo(self, request, queryset):
        total = 0
        for variante in queryset:
            if variante.stock_bloqueado > 0:
                total += variante.stock_bloqueado
                variante.stock_bloqueado = 0
                variante.save(update_fields=['stock_bloqueado'])
        self.message_user(
            request,
            f"Se liberaron {total} unidades bloqueadas.",
            messages.SUCCESS
        )
    liberar_bloqueo.short_description = "🔓 Liberar stock bloqueado"

    def save_model(self, request, obj, form, change):
        obj.clean()
        super().save_model(request, obj, form, change)
