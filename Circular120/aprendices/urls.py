# aprendices/urls.py
from django.urls import path
from .views import (
    DashboardView, AprendizListView, AprendizCreateView, AprendizUpdateView, AprendizDetailView,
    InasistenciaCreateView, InasistenciaListView, ActaCreateView, FileUploadView,
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

    # Actas
    path('actas/nueva/', ActaCreateView.as_view(), name='acta_create'),

    # Upload Excel (general)
    path('upload/', FileUploadView.as_view(), name='upload_file'),
    
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
]