from django import forms
from .models import Competencia, ResultadoAprendizaje


class CompetenciaForm(forms.ModelForm):
    class Meta:
        model = Competencia
        fields = ['codigo', 'nombre', 'programa', 'duracion_horas']


class ResultadoAprendizajeForm(forms.ModelForm):
    class Meta:
        model = ResultadoAprendizaje
        fields = ['codigo', 'descripcion', 'competencia']
