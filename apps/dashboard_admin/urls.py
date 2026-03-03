from django.urls import path
from .views import (
    ListaDiasConVentasView,
    DetalleVentasDiaView,
    KPIsGeneralesView,
    EstadisticasCategoriaView,
    CategoriasListView,
    SubcategoriasPorCategoriaView,
)

urlpatterns = [
    path("dias-ventas/", ListaDiasConVentasView.as_view()),
    path("detalle-ventas-dia/", DetalleVentasDiaView.as_view()),
    path("kpis-generales/", KPIsGeneralesView.as_view()),
    path("estadisticas-categoria/", EstadisticasCategoriaView.as_view(),
         name="estadisticas-categoria"),
    path("categorias/", CategoriasListView.as_view()),
    path("subcategorias/", SubcategoriasPorCategoriaView.as_view()),


]
