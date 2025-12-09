# apps/competencias/urls.py
from django.urls import path
from . import views

app_name = 'competencias'

urlpatterns = [
    path('', views.listar_competencias, name='listar'),
    path('crear/', views.crear_competencia, name='crear'),
    path('<int:pk>/', views.detalle_competencia, name='detalle'),
    path('ra/', views.listar_resultados_aprendizaje, name='listar_ra'),
    path('ra/crear/', views.crear_resultado_aprendizaje, name='crear_ra'),
]