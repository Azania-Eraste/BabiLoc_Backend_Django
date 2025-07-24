import django_filters
from .models import Bien

class BienFilter(django_filters.FilterSet):
    # Correction: utiliser 'tarifs' au lieu de 'Tarifs_Biens_id'
    prix_min = django_filters.NumberFilter(field_name="tarifs__prix", lookup_expr='gte')
    prix_max = django_filters.NumberFilter(field_name="tarifs__prix", lookup_expr='lte')
    ville = django_filters.CharFilter(field_name="ville__nom", lookup_expr='icontains')  # Aussi corriger pour ville
    type = django_filters.CharFilter(field_name="type_bien__nom", lookup_expr='icontains')

    class Meta:
        model = Bien
        fields = ['prix_min', 'prix_max', 'ville', 'type']
