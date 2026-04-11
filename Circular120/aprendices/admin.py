# aprendices/admin.py
from django.contrib import admin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateWidget
from import_export.admin import ImportExportModelAdmin
from .models import (
    Aprendiz, Ficha, Inasistencia, Competencia, 
    ResultadoAprendizaje, AprendizResultado, ActaComite,
    CentroFormacion, RolAdministrativo
)


# ==================== RESOURCES ====================

class AprendizResource(resources.ModelResource):
    """Resource para importar/exportar aprendices"""
    
    ficha = fields.Field(
        column_name='ficha',
        attribute='ficha',
        widget=ForeignKeyWidget(Ficha, 'numero')
    )
    
    fecha_inicio = fields.Field(
        column_name='fecha_inicio',
        attribute='fecha_inicio',
        widget=DateWidget(format='%d/%m/%Y')
    )
    
    fecha_final = fields.Field(
        column_name='fecha_final',
        attribute='fecha_final',
        widget=DateWidget(format='%d/%m/%Y')
    )
    
    class Meta:
        model = Aprendiz
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ['documento']
        fields = (
            'documento', 'nombre', 'apellido', 'email', 'telefono',
            'estado_formacion', 'ficha', 'fecha_inicio', 'fecha_final',
            'fecha_fin_lectiva', 'fecha_fin_productiva', 'observaciones'
        )
        export_order = fields


# ==================== ADMIN CLASSES ====================

@admin.register(CentroFormacion)
class CentroFormacionAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'municipio', 'telefono', 'activo']
    list_filter = ['activo', 'municipio']
    search_fields = ['codigo', 'nombre', 'municipio']
    list_editable = ['activo']


@admin.register(Ficha)
class FichaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'programa', 'centro', 'instructor', 'fecha_inicio', 'fecha_fin']
    list_filter = ['centro', 'fecha_inicio']
    search_fields = ['numero', 'programa', 'instructor']
    date_hierarchy = 'fecha_inicio'


@admin.register(Aprendiz)
class AprendizAdmin(ImportExportModelAdmin):
    resource_class = AprendizResource
    list_display = ['documento', 'nombre', 'apellido', 'ficha', 'estado_formacion', 'fecha_inicio']
    list_filter = ['estado_formacion', 'ficha']
    search_fields = ['documento', 'nombre', 'apellido']
    date_hierarchy = 'fecha_inicio'
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('documento', 'nombre', 'apellido', 'email', 'telefono')
        }),
        ('Información Académica', {
            'fields': ('ficha', 'estado_formacion')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_final', 'fecha_fin_lectiva', 'fecha_fin_productiva')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Inasistencia)
class InasistenciaAdmin(admin.ModelAdmin):
    list_display = ['aprendiz', 'ficha', 'fecha', 'justificada', 'reportado_por']
    list_filter = ['justificada', 'ficha', 'fecha']
    search_fields = ['aprendiz__documento', 'aprendiz__nombre', 'aprendiz__apellido']
    date_hierarchy = 'fecha'


@admin.register(Competencia)
class CompetenciaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre']
    search_fields = ['codigo', 'nombre']


@admin.register(ResultadoAprendizaje)
class ResultadoAprendizajeAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'competencia']
    list_filter = ['competencia']
    search_fields = ['codigo', 'nombre']


@admin.register(AprendizResultado)
class AprendizResultadoAdmin(admin.ModelAdmin):
    list_display = ['aprendiz', 'resultado', 'estado', 'fecha']
    list_filter = ['estado', 'fecha']
    search_fields = ['aprendiz__documento', 'aprendiz__nombre', 'resultado__codigo']
    date_hierarchy = 'fecha'


@admin.register(ActaComite)
class ActaComiteAdmin(admin.ModelAdmin):
    list_display = ['ficha', 'fecha', 'creado_por', 'created_at']
    list_filter = ['fecha', 'ficha']
    search_fields = ['ficha__numero', 'contenido']
    date_hierarchy = 'fecha'


@admin.register(RolAdministrativo)
class RolAdministrativoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo_rol', 'centro', 'activo', 'fecha_inicio', 'fecha_fin']
    list_filter = ['tipo_rol', 'centro', 'activo']
    search_fields = ['usuario__username', 'usuario__first_name', 'usuario__last_name']
    date_hierarchy = 'fecha_inicio'
    
    actions = ['deshabilitar_roles']
    
    fieldsets = (
        ('Usuario y Rol', {
            'fields': ('usuario', 'tipo_rol', 'centro')
        }),
        ('Periodo', {
            'fields': ('fecha_inicio', 'fecha_fin', 'activo')
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )
    
    def deshabilitar_roles(self, request, queryset):
        for rol in queryset:
            rol.deshabilitar()
        self.message_user(request, f'{queryset.count()} roles deshabilitados correctamente')
    deshabilitar_roles.short_description = 'Deshabilitar roles seleccionados'