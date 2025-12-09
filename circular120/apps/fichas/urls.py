# apps/fichas/urls.py
from django.urls import path
from . import views

app_name = 'fichas'

urlpatterns = [
    path('', views.listar_fichas, name='listar'),
    path('crear/', views.crear_ficha, name='crear'),
    path('<int:pk>/', views.detalle_ficha, name='detalle'),
    path('<int:pk>/aprendices/', views.aprendices_ficha, name='aprendices'),
    path('vencidas/', views.fichas_vencidas, name='vencidas'),
    path('alertas/', views.fichas_alertas, name='alertas'),
]