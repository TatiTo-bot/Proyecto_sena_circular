# aprendices/forms.py
from django import forms
from .models import Aprendiz, Inasistencia

class AprendizForm(forms.ModelForm):
    class Meta:
        model = Aprendiz
        fields = ['documento','nombre','apellido','email','telefono','estado_formacion','fecha_inicio','fecha_final','ficha','observaciones']

class InasistenciaForm(forms.ModelForm):
    class Meta:
        model = Inasistencia
        fields = ['aprendiz','ficha','fecha','justificada','motivo','reportado_por']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'motivo': forms.Textarea(attrs={'rows':2})
        }

class UploadFileForm(forms.Form):
    file = forms.FileField(label='Archivo Excel (.xls / .xlsx)', required=True)
