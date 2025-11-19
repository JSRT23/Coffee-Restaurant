from datetime import timedelta
from django.db.models import Count, F
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import *
from .serializers import *
from apps.pedidos.models import DetallePedido


# --------------------------------------------------
#  VIEWSETS  EXISTENTES
# --------------------------------------------------
class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


class SubCategoriaViewSet(viewsets.ModelViewSet):
    queryset = SubCategoria.objects.all()
    serializer_class = SubCategoriaSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

    # ----------  STOCK BAJO  ----------
    @action(detail=False, methods=['get'])
    def stock_bajo(self, request):
        qs = ProductoVariante.objects.filter(stock__lte=F('stock_minimo'))
        serializer = ProductoVarianteSerializer(qs, many=True)
        return Response(serializer.data)

    # ----------  ÚLTIMOS 10 NUEVOS  ----------
    @action(detail=False, methods=['get'])
    def nuevos(self, request):
        ultimos = (
            Producto.objects.filter(
                activo=True,
                variantes__activo=True,
                variantes__stock__gt=F('variantes__stock_bloqueado')
            )
            .order_by('-id')
            .distinct()[:10]
        )
        return Response(self._build_home_list(ultimos, request))

    # ----------  TOP 10 MÁS VENDIDOS  ----------
    @action(detail=False, methods=['get'])
    def mas_vendidos(self, request):
        from apps.pedidos.models import DetallePedido
        hace_30_dias = timezone.now() - timedelta(days=30)

        top = (
            Producto.objects.filter(
                activo=True,
                variantes__activo=True,
                variantes__stock__gt=F('variantes__stock_bloqueado'),
                variantes__detallepedido__pedido__fecha_pedido__gte=hace_30_dias,
                variantes__detallepedido__pedido__cancelado=False,
            )
            .annotate(unidades=Count('variantes__detallepedido__cantidad'))
            .order_by('-unidades')
            .distinct()[:10]
        )
        return Response(self._build_home_list(top, request))
    # ----------  HELPER COMÚN  ----------

    def _build_home_list(self, qs, request):
        def build_url(path): return request.build_absolute_uri(
            path) if path else None
        data = []

        for prod in qs:
            variantes_ok = prod.variantes.filter(
                activo=True, stock__gt=F('stock_bloqueado')
            )
            if not variantes_ok.exists():
                continue

            data.append({
                "id": prod.id,
                "nombre": prod.nombre,
                "descripcion": prod.descripcion,
                "imagen": build_url(prod.imagen.url) if prod.imagen else None,
                "variantes": [
                    {
                        "id": var.id,
                        "nombre_variante": var.nombre_variante,
                        "sku": var.sku,
                        "precio": float(var.precio),
                        "stock": var.stock_disponible,
                        "stock_minimo": var.stock_minimo,
                        "codigo_barras": var.codigo_barras,
                        "imagen_variante": build_url(var.imagen_variante.url)
                        if var.imagen_variante
                        else None,
                        "ubicacion": var.ubicacion.nombre if var.ubicacion else None,
                    }
                    for var in variantes_ok
                ],
            })
        return data

        # ----------  DETALLE DE UN PRODUCTO CON VARIANTES  ----------
    @action(detail=True, methods=['get'])
    def detalle_con_variantes(self, request, pk=None):
        """
        Devuelve un solo producto con sus variantes en stock.
        Usa el mismo helper que el menú.
        """
        producto = self.get_object()
        data = self._build_home_list([producto], request)
        # _build_home_list devuelve un array, tomamos el primer (y único) elemento
        return Response(data[0] if data else {"detail": "Sin variantes disponibles"}, status=200)


class ProductoVarianteViewSet(viewsets.ModelViewSet):
    queryset = ProductoVariante.objects.all()
    serializer_class = ProductoVarianteSerializer


class ProductosDisponiblesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductosDisponiblesSerializer

    def get_queryset(self):
        return ProductoVariante.objects.filter(stock__gt=F('stock_bloqueado'))


class MenuViewSet(viewsets.ViewSet):
    """
    Menú limpio: solo ramas con stock > 0.
    URLs absolutas para imágenes.
    """

    @action(detail=False, methods=['get'])
    def menu(self, request):
        def build_url(path): return request.build_absolute_uri(
            path) if path else None

        data = []
        categorias = (
            Categoria.objects.filter(estado=True)
            .prefetch_related("subcategorias__productos__variantes")
        )

        for cat in categorias:
            cat_data = {"categoria": cat.nombre, "subcategorias": []}

            for sub in cat.subcategorias.filter(estado=True):
                sub_data = {"nombre": sub.nombre, "productos": []}

                for prod in sub.productos.filter(activo=True):
                    variantes_disponibles = prod.variantes.filter(
                        activo=True, stock__gt=F("stock_bloqueado")
                    )

                    if variantes_disponibles.exists():
                        sub_data["productos"].append({
                            "id": prod.id,
                            "nombre": prod.nombre,
                            "descripcion": prod.descripcion,
                            "imagen": build_url(prod.imagen.url) if prod.imagen else None,
                            "variantes": [
                                {
                                    "id": var.id,
                                    "nombre_variante": var.nombre_variante,
                                    "sku": var.sku,
                                    "precio": float(var.precio),
                                    "stock": var.stock_disponible,
                                    "stock_minimo": var.stock_minimo,
                                    "codigo_barras": var.codigo_barras,
                                    "imagen_variante": build_url(var.imagen_variante.url)
                                    if var.imagen_variante
                                    else None,
                                    "ubicacion": var.ubicacion.nombre
                                    if var.ubicacion
                                    else None,
                                }
                                for var in variantes_disponibles
                            ],
                        })

                if sub_data["productos"]:
                    cat_data["subcategorias"].append(sub_data)

            if cat_data["subcategorias"]:
                data.append(cat_data)

        return Response(data)
