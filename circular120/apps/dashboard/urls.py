# apps/dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_principal, name='dashboard_principal'),
    path('riesgo-desercion/', views.aprendices_riesgo_desercion, name='aprendices_riesgo_desercion'),
    path('certificar-vencidos/', views.aprendices_certificar_vencidos, name='aprendices_certificar_vencidos'),
    path('proximos-vencer/', views.aprendices_proximos_vencer, name='aprendices_proximos_vencer'),
    path('baja-asistencia/', views.aprendices_baja_asistencia, name='aprendices_baja_asistencia'),
    path('caso/<str:tipo>/', views.dashboard_principal, name='detalle_caso'),
    path('ra-pendientes/', views.aprendices_ra_pendientes, name='aprendices_ra_pendientes'),
]
