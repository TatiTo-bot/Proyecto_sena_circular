
# apps/importador/urls.py
from django.urls import path
from . import views

app_name = 'importador'

urlpatterns = [
    path('inasistencias/', views.importar_inasistencias, name='importar_inasistencias'),
    path('evaluaciones/', views.importar_evaluaciones, name='importar_evaluaciones'),
    path('historial/', views.historial_importaciones, name='historial'),
    path('detalle/<int:pk>/', views.detalle_importacion, name='detalle'),
    path('descargar-plantilla/<str:tipo>/', views.descargar_plantilla, name='descargar_plantilla'),
]
