import django_filters
from .models import Bien

class BienFilter(django_filters.FilterSet):
    prix_min = django_filters.NumberFilter(field_name="prix", lookup_expr='gte')
    prix_max = django_filters.NumberFilter(field_name="prix", lookup_expr='lte')
    ville = django_filters.CharFilter(field_name="ville", lookup_expr='icontains')
    type = django_filters.CharFilter(field_name="Type__nom", lookup_expr='icontains')  # clé étrangère vers Type

    class Meta:
        model = Bien
        fields = ['prix_min', 'prix_max', 'ville', 'type']
