# apps/usuarios/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='usuarios/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='usuarios:login'), name='logout'),
    path('perfil/', views.perfil_usuario, name='perfil'),
    path('cambiar-password/', views.cambiar_password, name='cambiar_password'),
]