from django import forms
from .models import Ficha
from django.contrib.auth import get_user_model

User = get_user_model()


class FichaForm(forms.ModelForm):
    """Formulario para registrar/editar fichas"""
    
    class Meta:
        model = Ficha
        fields = [
            'numero', 'programa', 'fecha_inicio',
            'fecha_fin_lectiva', 'fecha_fin_practica',
            'instructor_lider', 'estado'
        ]
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'programa': forms.Select(attrs={'class': 'form-control'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin_lectiva': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin_practica': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'instructor_lider': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructor_lider'].queryset = User.objects.filter(is_active=True)
