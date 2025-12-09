from django.contrib import admin
from .models import Ficha, Programa


@admin.register(Programa)
class ProgramaAdmin(admin.ModelAdmin):
    search_fields = ['nombre']
    list_display = ['codigo', 'nombre', 'activo']


@admin.register(Ficha)
class FichaAdmin(admin.ModelAdmin):
    search_fields = ['numero']
    list_display = ['numero', 'programa', 'fecha_inicio', 'fecha_fin_lectiva', 'estado']
