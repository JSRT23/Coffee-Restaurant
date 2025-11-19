from django.db import models
from django.core.exceptions import ValidationError
import uuid

# ---------- Ubicación ----------


class Ubicacion(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.nombre

# ---------- Categoría ----------


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

# ---------- SubCategoría ----------


class SubCategoria(models.Model):
    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, related_name="subcategorias")
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Subcategoría"
        verbose_name_plural = "Subcategorías"
        unique_together = ("categoria", "nombre")
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.categoria.nombre} - {self.nombre}"

# ---------- Producto ----------


class Producto(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    subcategoria = models.ForeignKey(
        SubCategoria, on_delete=models.CASCADE, related_name='productos', null=True, blank=True)
    imagen = models.ImageField(
        upload_to='productos',  # ← dentro de MEDIA_ROOT
        null=True,
        blank=True
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

# ---------- ProductoVariante ----------


class ProductoVariante(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name='variantes')
    nombre_variante = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    stock_bloqueado = models.PositiveIntegerField(default=0, editable=False)
    ubicacion = models.ForeignKey(
        Ubicacion, on_delete=models.SET_NULL, null=True, blank=True)
    codigo_barras = models.CharField(
        max_length=50, blank=True, null=True, unique=True)
    ultima_compra = models.DateField(null=True, blank=True)
    activo = models.BooleanField()
    imagen_variante = models.ImageField(
        upload_to='variantes',  # ← dentro de MEDIA_ROOT
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.producto.nombre} - {self.nombre_variante}"

    # --- PROPIEDADES ---

    @property
    def stock_disponible(self):
        return max(0, self.stock - self.stock_bloqueado)

    @property
    def alerta_stock(self):
        return self.stock_disponible <= self.stock_minimo

    @property
    def margen(self):
        return ((self.precio - self.costo) / self.precio * 100) if self.costo else 0

    # --- MÉTODOS DE STOCK ---
    def bloquear(self, cantidad):
        if cantidad > self.stock_disponible:
            raise ValidationError("No hay stock suficiente para bloquear.")
        self.stock_bloqueado += cantidad
        self.save(update_fields=['stock_bloqueado'])

    def desbloquear(self, cantidad):
        self.stock_bloqueado = max(0, self.stock_bloqueado - cantidad)
        self.save(update_fields=['stock_bloqueado'])

    def descontar(self, cantidad):
        if cantidad > self.stock_disponible:
            raise ValidationError("No hay stock suficiente para descontar.")
        self.stock -= cantidad
        self.save(update_fields=['stock'])

    # --- VALIDACIONES ---
    def clean(self):
        if self.precio < 0:
            raise ValidationError("El precio no puede ser negativo.")
        if self.stock < 0:
            raise ValidationError("El stock no puede ser negativo.")
        if self.costo < 0:
            raise ValidationError("El costo no puede ser negativo.")

    # --- SAVE ---
    def save(self, *args, **kwargs):
        if not self.codigo_barras:
            self.codigo_barras = str(
                uuid.uuid4()).replace('-', '').upper()[:12]
        # Activo según stock disponible
        self.activo = self.stock_disponible > 0
        super().save(*args, **kwargs)
        # 3. después de guardar, refrescamos por si alguien tocó solo stock
        self.refresh_from_db(fields=['stock', 'stock_bloqueado'])
        if self.stock_disponible == 0 and self.activo:
            # fuerza el flag a False sin entrar en recursión
            self.activo = False
            super().save(update_fields=['activo'])
