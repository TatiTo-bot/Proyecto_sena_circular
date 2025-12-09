from django import forms
from django.core.exceptions import ValidationError
from apps.aprendices.models import Aprendiz
from apps.fichas.models import Ficha
from django.conf import settings


class AprendizForm(forms.ModelForm):
    """Formulario para registrar/editar aprendices"""
    
    class Meta:
        model = Aprendiz
        fields = [
            'tipo_documento', 'documento', 'nombre', 'apellido',
            'email', 'telefono', 'ficha', 'estado_formacion', 'observaciones'
        ]
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
            'documento': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'ficha': forms.Select(attrs={'class': 'form-control'}),
            'estado_formacion': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        dominios_permitidos = settings.CIRCULAR_120['EMAILS_INSTITUCIONALES_PERMITIDOS']

        if not any(email.endswith(dominio) for dominio in dominios_permitidos):
            raise ValidationError(
                f'El correo debe ser institucional del SENA. Dominios permitidos: {", ".join(dominios_permitidos)}'
            )

        return email


class BuscarAprendizForm(forms.Form):
    busqueda = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    ficha = forms.ModelChoiceField(
        queryset=Ficha.objects.all().order_by('-numero'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    estado_formacion = forms.ChoiceField(
        choices=[('', 'Todos')] + list(Aprendiz.ESTADOS_FORMACION),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
