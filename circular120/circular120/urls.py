from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('apps.dashboard.urls')),   # ✅ AQUI VA EL INICIO
    path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('aprendices/', include('apps.aprendices.urls')),
    path('fichas/', include('apps.fichas.urls')),
    path('competencias/', include('apps.competencias.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('importador/', include('apps.importador.urls')),
]
