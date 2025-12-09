# apps/aprendices/urls.py
from django.urls import path
from . import views

app_name = 'aprendices'

urlpatterns = [
    path('', views.lista_aprendices, name='listar'),
    path('crear/', views.crear_aprendiz, name='crear'),
    path('<int:pk>/', views.detalle_aprendiz, name='detalle'),
    path('<int:pk>/editar/', views.editar_aprendiz, name='editar'),
    path('<int:pk>/historial/', views.historial_aprendiz, name='historial'),
    path('buscar/', views.buscar_aprendiz, name='buscar'),
]
