from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet)
router.register(r'subcategorias', SubCategoriaViewSet)
# NO registres 'productos' aquí si vas a usar paths custom
# router.register(r'productos', ProductoViewSet)  ← comenta o elimina
router.register(r'variantes', ProductoVarianteViewSet)
router.register(r'productos_disponibles',
                ProductosDisponiblesViewSet, basename='productos_disponibles')
router.register(r'menu', MenuViewSet, basename='menu')
router.register(r'productos', ProductoViewSet, basename='productos')

urlpatterns = [
    # 1. tus paths custom
    path('productos/nuevos/',
         ProductoViewSet.as_view({'get': 'nuevos'}), name='productos-nuevos'),
    path('productos/mas-vendidos/',
         ProductoViewSet.as_view({'get': 'mas_vendidos'}), name='productos-mas-vendidos'),
    path('productos/<int:pk>/detalle-con-variantes/', ProductoViewSet.as_view(
        {'get': 'detalle_con_variantes'}), name='producto-detalle-variantes'),
    # 2. después el router (sin 'productos' dentro)
    path('', include(router.urls)),
]
