from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.dashboard_admin.services import (
    obtener_dias_con_ventas,
    obtener_detalle_ventas_por_dia,
    obtener_kpis_generales,
    obtener_estadisticas_categoria,
    obtener_categorias,
    obtener_subcategorias_por_categoria,
)

from apps.dashboard_admin.serializers import (
    DiaVentasSerializer,
    DetalleVentasDiaSerializer,
    KPIsGeneralesSerializer
)


class EsAdminPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.rol == "ADMIN"


# 📅 LIBRO DE DÍAS CON VENTAS
class ListaDiasConVentasView(APIView):
    permission_classes = [EsAdminPermission]

    def get(self, request):
        dias = obtener_dias_con_ventas()
        serializer = DiaVentasSerializer(dias, many=True)
        return Response(serializer.data)


# 📊 DETALLE COMPLETO DE UN DÍA
class DetalleVentasDiaView(APIView):
    permission_classes = [EsAdminPermission]

    def get(self, request):

        fecha = request.query_params.get("fecha")

        if not fecha:
            return Response(
                {"error": "Debe enviar la fecha en formato YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = obtener_detalle_ventas_por_dia(fecha)
        serializer = DetalleVentasDiaSerializer(data)

        return Response(serializer.data)


# 🚀 KPIs GENERALES DEL DASHBOARD

class KPIsGeneralesView(APIView):
    permission_classes = [EsAdminPermission]

    def get(self, request):
        data = obtener_kpis_generales()
        return Response(data, status=status.HTTP_200_OK)


class EstadisticasCategoriaView(APIView):
    permission_classes = [EsAdminPermission]

    def get(self, request):
        categoria_id = request.query_params.get("categoria")
        subcategoria_id = request.query_params.get("subcategoria")

        if not categoria_id:
            return Response(
                {"error": "Debe enviar el parámetro 'categoria'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = obtener_estadisticas_categoria(
            categoria_id=categoria_id,
            subcategoria_id=subcategoria_id
        )

        return Response(data, status=status.HTTP_200_OK)


class CategoriasListView(APIView):

    def get(self, request):
        data = obtener_categorias()
        return Response(data)


class SubcategoriasPorCategoriaView(APIView):

    def get(self, request):
        categoria_id = request.query_params.get("categoria")

        if not categoria_id:
            return Response(
                {"error": "Debe enviar categoria"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = obtener_subcategorias_por_categoria(categoria_id)
        return Response(data)
