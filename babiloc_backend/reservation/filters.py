import django_filters
from .models import Bien

class BienFilter(django_filters.FilterSet):
    prix_min = django_filters.NumberFilter(field_name="Tarifs_Biens_id__prix", lookup_expr='gte')
    prix_max = django_filters.NumberFilter(field_name="Tarifs_Biens_id__prix", lookup_expr='lte')
    ville = django_filters.CharFilter(field_name="ville__nom", lookup_expr='icontains')
    type = django_filters.CharFilter(field_name="type_bien__nom", lookup_expr='icontains')  # Correction : utiliser 'type_bien__nom' au lieu de 'Type__nom'

    class Meta:
        model = Bien
        fields = ['prix_min', 'prix_max', 'ville', 'type']
