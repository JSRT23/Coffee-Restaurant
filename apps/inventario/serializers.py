from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import Ubicacion, Categoria, SubCategoria, Producto, ProductoVariante


# ---------- Ubicación ----------
class UbicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ubicacion
        fields = '__all__'

    def validate_nombre(self, value):
        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres.")
        return value


# ---------- Categoría ----------
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

    def validate_nombre(self, value):
        if Categoria.objects.filter(nombre=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError(
                "Ya existe una categoría con este nombre.")
        return value


# ---------- SubCategoría ----------
class SubCategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategoria
        fields = '__all__'

    def validate(self, data):
        categoria = data.get("categoria")
        nombre = data.get("nombre")
        if SubCategoria.objects.filter(categoria=categoria, nombre=nombre).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError(
                "Ya existe una subcategoría con ese nombre en esta categoría.")
        return data


# ---------- Producto ----------
class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

    def validate_nombre(self, value):
        if len(value) < 2:
            raise serializers.ValidationError(
                "El nombre del producto debe tener al menos 2 caracteres.")
        return value


# ---------- ProductoVariante ----------
class ProductoVarianteSerializer(serializers.ModelSerializer):
    stock_disponible = serializers.ReadOnlyField()
    alerta_stock = serializers.ReadOnlyField()
    margen = serializers.ReadOnlyField()
    activo = serializers.ReadOnlyField()

    class Meta:
        model = ProductoVariante
        fields = '__all__'

    def validate_precio(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El precio no puede ser negativo.")
        return value

    def validate_costo(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El costo no puede ser negativo.")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El stock no puede ser negativo.")
        return value

    def validate_stock_minimo(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El stock mínimo no puede ser negativo.")
        return value

    def validate(self, data):

        if data.get("costo") and data.get("precio") and data["costo"] > data["precio"]:
            raise serializers.ValidationError(
                "El costo no puede ser mayor que el precio.")
        return data


class ProductosDisponiblesSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)  # 👈 Aquí también lo anidamos

    class Meta:
        model = ProductoVariante
        fields = '__all__'
