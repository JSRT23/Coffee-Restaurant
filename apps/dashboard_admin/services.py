from collections import defaultdict
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncMonth
from apps.pedidos.models import Pedido, DetallePedido
from apps.usuarios.models import Usuario
from django.utils import timezone
from datetime import timedelta
from apps.inventario.models import Categoria, SubCategoria


def obtener_dias_con_ventas():
    dias = (
        Pedido.objects
        .filter(cancelado=False)
        .annotate(fecha_dia=TruncDate("fecha_pedido"))
        .values("fecha_dia")
        .annotate(total_dia=Sum("total"))
        .order_by("-fecha_dia")
    )
    return dias


def obtener_detalle_ventas_por_dia(fecha):

    pedidos = Pedido.objects.filter(
        fecha_pedido__date=fecha,
        cancelado=False
    )

    total_general = pedidos.aggregate(total=Sum("total"))["total"] or 0

    total_efectivo = pedidos.filter(
        metodo_pago__nombre__iexact="efectivo"
    ).aggregate(total=Sum("total"))["total"] or 0

    total_transferencia = pedidos.filter(
        metodo_pago__nombre__iexact="transferencia"
    ).aggregate(total=Sum("total"))["total"] or 0

    detalles = DetallePedido.objects.filter(
        pedido__in=pedidos
    ).select_related(
        "variante__producto__subcategoria__categoria"
    )

    estructura = defaultdict(lambda: {
        "cantidad_total": 0,
        "total_dinero": 0,
        "subcategorias": defaultdict(lambda: {
            "cantidad_total": 0,
            "total_dinero": 0,
            "productos": defaultdict(lambda: {
                "cantidad_total": 0,
                "total_dinero": 0
            })
        })
    })

    cantidad_total_productos = 0

    for detalle in detalles:
        categoria = detalle.variante.producto.subcategoria.categoria.nombre
        subcategoria = detalle.variante.producto.subcategoria.nombre
        producto = detalle.variante.producto.nombre

        cantidad = detalle.cantidad
        subtotal = detalle.subtotal

        cantidad_total_productos += cantidad

        estructura[categoria]["cantidad_total"] += cantidad
        estructura[categoria]["total_dinero"] += subtotal

        estructura[categoria]["subcategorias"][subcategoria]["cantidad_total"] += cantidad
        estructura[categoria]["subcategorias"][subcategoria]["total_dinero"] += subtotal

        estructura[categoria]["subcategorias"][subcategoria]["productos"][producto]["cantidad_total"] += cantidad
        estructura[categoria]["subcategorias"][subcategoria]["productos"][producto]["total_dinero"] += subtotal

    categorias_list = []

    for cat_nombre, cat_data in estructura.items():
        subcategorias_list = []

        for sub_nombre, sub_data in cat_data["subcategorias"].items():
            productos_list = []

            for prod_nombre, prod_data in sub_data["productos"].items():
                productos_list.append({
                    "producto": prod_nombre,
                    "cantidad_total": prod_data["cantidad_total"],
                    "total_dinero": prod_data["total_dinero"],
                })

            subcategorias_list.append({
                "subcategoria": sub_nombre,
                "cantidad_total": sub_data["cantidad_total"],
                "total_dinero": sub_data["total_dinero"],
                "productos": productos_list
            })

        categorias_list.append({
            "categoria": cat_nombre,
            "cantidad_total": cat_data["cantidad_total"],
            "total_dinero": cat_data["total_dinero"],
            "subcategorias": subcategorias_list
        })

    return {
        "fecha": fecha,
        "total_general": total_general,
        "total_efectivo": total_efectivo,
        "total_transferencia": total_transferencia,
        "cantidad_total_productos": cantidad_total_productos,
        "categorias": categorias_list
    }


def obtener_kpis_generales():
    hoy = timezone.now()

    # MES ACTUAL
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if hoy.month == 12:
        fin_mes = inicio_mes.replace(year=hoy.year + 1, month=1)
    else:
        fin_mes = inicio_mes.replace(month=hoy.month + 1)

    # SEMANA ACTUAL (lunes 00:00 → lunes siguiente)
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_semana = inicio_semana.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    fin_semana = inicio_semana + timedelta(days=7)

    # FILTRO BASE
    pedidos = Pedido.objects.filter(
        cancelado=False,
        estado__nombre__iexact="Entregado"
    )

    # TOTAL MES
    total_mes = pedidos.filter(
        fecha_pedido__gte=inicio_mes,
        fecha_pedido__lt=fin_mes
    ).aggregate(total=Sum("total"))["total"] or 0

    # TOTAL SEMANA
    total_semana = pedidos.filter(
        fecha_pedido__gte=inicio_semana,
        fecha_pedido__lt=fin_semana
    ).aggregate(total=Sum("total"))["total"] or 0

    # TICKET PROMEDIO
    total_general = pedidos.aggregate(total=Sum("total"))["total"] or 0
    cantidad_pedidos = pedidos.count()
    ticket_promedio = total_general / cantidad_pedidos if cantidad_pedidos > 0 else 0

    # PRODUCTO TOP
    producto_top = (
        DetallePedido.objects
        .filter(
            pedido__cancelado=False,
            pedido__estado__nombre__iexact="Entregado"
        )
        .values(
            "variante__producto__nombre",
            "variante__nombre_variante"
        )
        .annotate(total_vendido=Sum("cantidad"))
        .order_by("-total_vendido")
        .first()
    )

    # MESES HISTÓRICOS
    meses = (
        pedidos
        .annotate(mes=TruncMonth("fecha_pedido"))
        .values("mes")
        .annotate(total=Sum("total"))
        .order_by("-mes")
    )

    meses_list = [
        {
            "mes": mes["mes"].strftime("%Y-%m"),
            "total": mes["total"] or 0
        }
        for mes in meses
    ]

    # SEMANAS REALES DEL MES (lunes → lunes)
    semanas = []

    primer_lunes = inicio_mes
    while primer_lunes.weekday() != 0:
        primer_lunes += timedelta(days=1)

    semana_inicio = primer_lunes

    while semana_inicio < fin_mes:
        semana_fin = semana_inicio + timedelta(days=7)

        total_sem = pedidos.filter(
            fecha_pedido__gte=semana_inicio,
            fecha_pedido__lt=semana_fin
        ).aggregate(total=Sum("total"))["total"] or 0

        semanas.append({
            "inicio": semana_inicio.strftime("%Y-%m-%d"),
            "fin": semana_fin.strftime("%Y-%m-%d"),
            "total": total_sem
        })

        semana_inicio = semana_fin

    return {
        "total_ventas_mes": total_mes,
        "total_ventas_semana": total_semana,
        "ticket_promedio": ticket_promedio,
        "producto_mas_vendido": producto_top,
        "meses": meses_list,
        "semanas": semanas,
    }


def obtener_estadisticas_categoria(categoria_id, subcategoria_id=None):

    detalles = DetallePedido.objects.filter(
        pedido__cancelado=False,
        pedido__estado__nombre__iexact="Entregado",
        variante__producto__subcategoria__categoria__id=categoria_id
    )

    if subcategoria_id:
        detalles = detalles.filter(
            variante__producto__subcategoria__id=subcategoria_id
        )

    productos = (
        detalles
        .values(
            "variante__producto__id",
            "variante__producto__nombre"
        )
        .annotate(total_vendido=Sum("cantidad"))
        .order_by("-total_vendido")
    )

    variantes = (
        detalles
        .values(
            "variante__id",
            "variante__nombre_variante",
            "variante__producto__nombre"
        )
        .annotate(total_vendido=Sum("cantidad"))
        .order_by("-total_vendido")
    )

    return {
        "productos": list(productos),
        "variantes": list(variantes),
    }


def obtener_categorias():
    return Categoria.objects.all().values("id", "nombre")


def obtener_subcategorias_por_categoria(categoria_id):
    return SubCategoria.objects.filter(
        categoria_id=categoria_id
    ).values("id", "nombre")
