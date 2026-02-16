# aprendices/forms.py
from django import forms
from .models import Aprendiz, Inasistencia, Ficha

class AprendizForm(forms.ModelForm):
    class Meta:
        model = Aprendiz
        fields = [
            'documento', 'nombre', 'apellido', 'email', 'telefono',
            'estado_formacion', 'fecha_inicio', 'fecha_final',
            'fecha_fin_lectiva', 'fecha_fin_productiva',
            'ficha', 'observaciones'
        ]
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_final': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin_lectiva': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin_productiva': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'documento': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'estado_formacion': forms.Select(attrs={'class': 'form-control'}),
            'ficha': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'documento': 'Documento de Identidad',
            'nombre': 'Nombre',
            'apellido': 'Apellido',
            'email': 'Correo Electrónico',
            'telefono': 'Teléfono',
            'estado_formacion': 'Estado de Formación',
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_final': 'Fecha Final',
            'fecha_fin_lectiva': 'Fecha Fin Etapa Lectiva',
            'fecha_fin_productiva': 'Fecha Fin Etapa Productiva',
            'ficha': 'Ficha',
            'observaciones': 'Observaciones',
        }

class InasistenciaForm(forms.ModelForm):
    class Meta:
        model = Inasistencia
        fields = ['aprendiz', 'ficha', 'fecha', 'justificada', 'motivo', 'reportado_por']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'motivo': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'aprendiz': forms.Select(attrs={'class': 'form-control'}),
            'ficha': forms.Select(attrs={'class': 'form-control'}),
            'justificada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reportado_por': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'aprendiz': 'Aprendiz',
            'ficha': 'Ficha',
            'fecha': 'Fecha de Inasistencia',
            'justificada': '¿Justificada?',
            'motivo': 'Motivo',
            'reportado_por': 'Reportado Por',
        }

class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        fields = ['numero', 'programa', 'instructor', 'fecha_inicio', 'fecha_fin']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 2756890'}),
            'programa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Tecnología en Análisis y Desarrollo de Software'}),
            'instructor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del instructor principal'}),
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'numero': 'Número de Ficha',
            'programa': 'Programa de Formación',
            'instructor': 'Instructor Principal',
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_fin': 'Fecha de Finalización',
        }

class UploadFileForm(forms.Form):
    file = forms.FileField(
        label='Archivo Excel (.xls / .xlsx)',
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xls,.xlsx'})
    )

class UploadFichaDataForm(forms.Form):
    """Formulario para subir datos específicos de una ficha"""
    ficha = forms.ModelChoiceField(
        queryset=Ficha.objects.all(),
        label='Seleccionar Ficha',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Selecciona la ficha a la que pertenecen los datos que vas a importar'
    )
    
    tipo_datos = forms.ChoiceField(
        label='Tipo de Datos a Importar',
        choices=[
            ('inasistencias', 'Inasistencias'),
            ('juicios', 'Juicios Evaluativos'),
            ('aprendices', 'Lista de Aprendices'),
            ('mixto', 'Datos Mixtos (Inasistencias + Juicios)')
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Indica qué tipo de información contiene el archivo'
    )
    
    archivo = forms.FileField(
        label='Archivo Excel',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xls,.xlsx'}),
        help_text='Archivo Excel con los datos de la ficha seleccionada'
    )
    
    sobrescribir = forms.BooleanField(
        label='Sobrescribir datos existentes',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Si está marcado, los datos existentes serán reemplazados'
    )