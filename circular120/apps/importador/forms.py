from django import forms
from django.core.exceptions import ValidationError
from .models import ArchivoImportado
from apps.fichas.models import Ficha

class ImportarExcelForm(forms.Form):
    archivo = forms.FileField()

class ImportarInasistenciasForm(forms.Form):
    """Formulario para importar archivo Excel de inasistencias"""
    
    archivo = forms.FileField(
        label='Archivo Excel',
        help_text='Formatos permitidos: .xls, .xlsx (máx 10MB)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xls,.xlsx'
        })
    )
    
    ficha = forms.ModelChoiceField(
        queryset=Ficha.objects.filter(estado='ACTIVA').select_related('programa'),
        label='Ficha',
        help_text='Seleccione la ficha a la que corresponden las inasistencias',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        
        if not archivo.name.endswith(('.xls', '.xlsx')):
            raise ValidationError('Solo se permiten archivos Excel (.xls, .xlsx)')
        
        if archivo.size > 10 * 1024 * 1024:
            raise ValidationError('El archivo no puede superar los 10MB')
        
        return archivo


class ImportarEvaluacionesForm(forms.Form):
    """Formulario para importar archivo Excel de juicios evaluativos"""
    
    archivo = forms.FileField(
        label='Archivo Excel',
        help_text='Formatos permitidos: .xls, .xlsx (máx 10MB)',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xls,.xlsx'
        })
    )
    
    ficha = forms.ModelChoiceField(
        queryset=Ficha.objects.filter(estado='ACTIVA').select_related('programa'),
        label='Ficha',
        help_text='Seleccione la ficha a la que corresponden las evaluaciones',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        
        if not archivo.name.endswith(('.xls', '.xlsx')):
            raise ValidationError('Solo se permiten archivos Excel (.xls, .xlsx)')
        
        if archivo.size > 10 * 1024 * 1024:
            raise ValidationError('El archivo no puede superar los 10MB')
        
        return archivo
