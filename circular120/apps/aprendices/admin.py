from django.contrib import admin
from django.utils.html import format_html
from .models import Aprendiz
from apps.fichas.models import Ficha, Programa


@admin.register(Aprendiz)
class AprendizAdmin(admin.ModelAdmin):
    list_display = [
        'documento', 'nombre_completo', 'email', 'ficha',
        'estado_formacion', 'activo'
    ]

    list_filter = ['estado_formacion', 'activo', 'tipo_documento']
    search_fields = ['documento', 'nombre', 'apellido', 'email']
    readonly_fields = ['fecha_registro', 'fecha_actualizacion']
    autocomplete_fields = ['ficha']

    fieldsets = (
        ('Información Personal', {
            'fields': ('tipo_documento', 'documento', 'nombre', 'apellido', 'email', 'telefono')
        }),
        ('Información Académica', {
            'fields': ('ficha', 'estado_formacion', 'activo', 'observaciones')
        }),
        ('Información del Sistema', {
            'fields': ('fecha_registro', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
