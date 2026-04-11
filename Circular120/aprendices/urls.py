# aprendices/urls.py
from django.urls import path
from .views_import import import_excel
from .views_import import import_excel, import_inasistencias
from . import views
from .views import (
    DashboardView, AprendizListView, AprendizCreateView, AprendizUpdateView, AprendizDetailView,
    InasistenciaCreateView, InasistenciaListView, ActaCreateView,
    casos_por_certificar, casos_vencidos, reporte_circular120,
    aprobar_certificacion, cancelar_aprendiz
)

# Importar las nuevas vistas de fichas
from .views_fichas import (
    FichaListView, FichaCreateView, FichaUpdateView, FichaDetailView,
    FichaUploadDataView
)

urlpatterns = [
    # Dashboard
    path('', DashboardView.as_view(), name='dashboard'),
    
    # CRUD Aprendices
    path('aprendices/', AprendizListView.as_view(), name='aprendiz_list'),
    path('aprendices/nuevo/', AprendizCreateView.as_view(), name='aprendiz_create'),
    path('aprendices/<str:pk>/editar/', AprendizUpdateView.as_view(), name='aprendiz_update'),
    path('aprendices/<str:pk>/', AprendizDetailView.as_view(), name='aprendiz_detail'),

    # Inasistencias
    path('inasistencias/', InasistenciaListView.as_view(), name='inasistencia_list'),
    path('inasistencias/nuevo/', InasistenciaCreateView.as_view(), name='inasistencia_create'),
    path('importar/inasistencias/', import_inasistencias, name='import_inasistencias'),

    # Actas
    path('actas/nueva/', ActaCreateView.as_view(), name='acta_create'),
    
    # ===== IMPORTACIÓN (NUEVA VERSIÓN CON DJANGO-IMPORT-EXPORT) =====
    path('upload/', import_excel, name='upload_file'),  # ← CAMBIADO: Ahora usa import_excel
    path('import/', import_excel, name='import_excel'),  # ← Mantener por compatibilidad
    
    # ===== GESTIÓN DE FICHAS =====
    path('fichas/', FichaListView.as_view(), name='ficha_list'),
    path('fichas/nueva/', FichaCreateView.as_view(), name='ficha_create'),
    path('fichas/<str:pk>/editar/', FichaUpdateView.as_view(), name='ficha_update'),
    path('fichas/<str:pk>/', FichaDetailView.as_view(), name='ficha_detail'),
    path('fichas/<str:numero_ficha>/subir-datos/', FichaUploadDataView.as_view(), name='ficha_upload_data'),
    
    # ===== CIRCULAR 120 =====
    path('por-certificar/', casos_por_certificar, name='casos_por_certificar'),
    path('vencidos/', casos_vencidos, name='casos_vencidos'),
    path('reporte-circular120/', reporte_circular120, name='reporte_circular120'),
    
    # Acciones
    path('aprobar/<str:documento>/', aprobar_certificacion, name='aprobar_certificacion'),
    path('cancelar/<str:documento>/', cancelar_aprendiz, name='cancelar_aprendiz'),
    
    # Reportes
    path('reportes/inasistencias/', views.descargar_reporte_inasistencias, name='reporte_inasistencias_excel'),
    path('reportes/juicios/', views.descargar_reporte_juicios, name='reporte_juicios_excel'),
    path('reportes/circular120/', views.descargar_reporte_circular120, name='reporte_circular120_excel'),
    path('reportes/generar-todos/', views.generar_todos_reportes_view, name='generar_todos_reportes'),
]