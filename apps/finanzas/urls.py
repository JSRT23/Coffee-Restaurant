from django.urls import path
from .views import (
    EstadoCreditoViewSet,
    TipoMovimientoViewSet,
    CreditoViewSet,
    MovimientoCreditoViewSet,
    AuditoriaCreditoViewSet,
    EstadoSolicitudViewSet,
    SolicitudAcreditacionViewSet,
    CreditoListMeseroView,
    registrar_abono_mesero,
)

# Vistas existentes
estado_list = EstadoCreditoViewSet.as_view({
    "get": "list",
    "post": "create"
})
estado_detail = EstadoCreditoViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})

tipo_list = TipoMovimientoViewSet.as_view({
    "get": "list",
    "post": "create"
})
tipo_detail = TipoMovimientoViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})

credito_list = CreditoViewSet.as_view({
    "get": "list",
    "post": "create"
})
credito_detail = CreditoViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})
credito_consumir = CreditoViewSet.as_view({"post": "consumir"})
credito_pagar = CreditoViewSet.as_view({"post": "pagar"})
credito_movimientos = CreditoViewSet.as_view({"get": "movimientos"})
credito_auditorias = CreditoViewSet.as_view({"get": "auditorias"})

movimiento_list = MovimientoCreditoViewSet.as_view({
    "get": "list",
    "post": "create"
})
movimiento_detail = MovimientoCreditoViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})

# Nuevas vistas de acreditación
estado_solicitud_list = EstadoSolicitudViewSet.as_view({"get": "list"})
solicitud_list = SolicitudAcreditacionViewSet.as_view({
    "get": "list",
    "post": "create"
})
solicitud_detail = SolicitudAcreditacionViewSet.as_view({
    "get": "retrieve",
    "put": "update",
    "patch": "partial_update",
    "delete": "destroy"
})
solicitud_responder = SolicitudAcreditacionViewSet.as_view(
    {"patch": "responder"})

urlpatterns = [
    # Estados de crédito
    path("estados/", estado_list, name="estado-list"),
    path("estados/<int:pk>/", estado_detail, name="estado-detail"),

    # Tipos de movimiento
    path("tipos/", tipo_list, name="tipo-list"),
    path("tipos/<int:pk>/", tipo_detail, name="tipo-detail"),

    # Créditos
    path("creditos/", credito_list, name="credito-list"),
    path("creditos/<int:pk>/", credito_detail, name="credito-detail"),
    path("creditos/<int:pk>/consumir/",
         credito_consumir, name="credito-consumir"),
    path("creditos/<int:pk>/pagar/", credito_pagar, name="credito-pagar"),
    path("creditos/<int:pk>/movimientos/",
         credito_movimientos, name="credito-movimientos"),
    path("creditos/<int:pk>/auditorias/",
         credito_auditorias, name="credito-auditorias"),

    # Movimientos
    path("movimientos/", movimiento_list, name="movimiento-list"),
    path("movimientos/<int:pk>/", movimiento_detail, name="movimiento-detail"),

    # Auditorias
    path("auditorias/",
         AuditoriaCreditoViewSet.as_view({"get": "list"}), name="auditoria-list"),

    # Acreditación
    path("solicitudes/estados/", estado_solicitud_list,
         name="estado-solicitud-list"),
    path("solicitudes/", solicitud_list, name="solicitud-list"),
    path("solicitudes/<int:pk>/", solicitud_detail, name="solicitud-detail"),
    path("solicitudes/<int:pk>/responder/",
         solicitud_responder, name="solicitud-responder"),
    path("mesero/creditos/", CreditoListMeseroView.as_view(),
         name="mesero-creditos-list"),
    path("mesero/abono/", registrar_abono_mesero, name="mesero-registrar-abono"),
]
