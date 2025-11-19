import django_filters as df
from .models import MovimientoCredito, TipoMovimiento


class MovimientoFilter(df.FilterSet):
    fecha_desde = df.DateTimeFilter(field_name="fecha", lookup_expr="gte")
    fecha_hasta = df.DateTimeFilter(field_name="fecha", lookup_expr="lte")
    tipo = df.ModelChoiceFilter(queryset=TipoMovimiento.objects.all())

    class Meta:
        model = MovimientoCredito
        fields = ["tipo", "fecha_desde", "fecha_hasta"]
