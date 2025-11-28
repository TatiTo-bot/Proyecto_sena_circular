# aprendices/urls.py
from django.urls import path
from .views import (
    DashboardView, AprendizListView, AprendizCreateView, AprendizUpdateView, AprendizDetailView,
    InasistenciaCreateView, InasistenciaListView, ActaCreateView, FileUploadView
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('aprendices/', AprendizListView.as_view(), name='aprendiz_list'),
    path('aprendices/nuevo/', AprendizCreateView.as_view(), name='aprendiz_create'),
    path('aprendices/<str:pk>/editar/', AprendizUpdateView.as_view(), name='aprendiz_update'),
    path('aprendices/<str:pk>/', AprendizDetailView.as_view(), name='aprendiz_detail'),

    path('inasistencias/', InasistenciaListView.as_view(), name='inasistencia_list'),
    path('inasistencias/nuevo/', InasistenciaCreateView.as_view(), name='inasistencia_create'),

    path('actas/nueva/', ActaCreateView.as_view(), name='acta_create'),

    path('upload/', FileUploadView.as_view(), name='upload_file'),
]
