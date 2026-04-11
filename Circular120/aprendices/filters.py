# aprendices/filters.py
import django_filters
from .models import Aprendiz, Ficha, CentroFormacion

class AprendizFilter(django_filters.FilterSet):
    """Filtros para la lista de aprendices"""
    
    ficha = django_filters.ModelChoiceFilter(
        queryset=Ficha.objects.all(),
        label='Ficha',
        empty_label='Todas las fichas'
    )
    
    estado_formacion = django_filters.ChoiceFilter(
        choices=Aprendiz.ESTADO_FORMACION_CHOICES,
        label='Estado de Formación',
        empty_label='Todos los estados'
    )
    
    nombre = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Buscar por nombre'
    )
    
    apellido = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Buscar por apellido'
    )
    
    documento = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Buscar por documento'
    )
    
    class Meta:
        model = Aprendiz
        fields = ['ficha', 'estado_formacion', 'nombre', 'apellido', 'documento']


class FichaFilter(django_filters.FilterSet):
    """Filtros para la lista de fichas"""
    
    centro = django_filters.ModelChoiceFilter(
        queryset=CentroFormacion.objects.filter(activo=True),
        label='Centro de Formación',
        empty_label='Todos los centros'
    )
    
    programa = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Buscar programa'
    )
    
    numero = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Número de ficha'
    )
    
    class Meta:
        model = Ficha
        fields = ['centro', 'programa', 'numero']