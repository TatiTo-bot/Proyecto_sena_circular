from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from apps.usuarios.models import HistorialAcceso


class ActualizarUltimoAccesoMiddleware:
    """
    Middleware para actualizar el último acceso del usuario
    y registrar en el historial
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Antes de procesar la vista
        if request.user.is_authenticated:
            # Actualizar último acceso en perfil
            if hasattr(request.user, 'perfil'):
                request.user.perfil.ultimo_acceso = timezone.now()
                request.user.perfil.save(update_fields=['ultimo_acceso'])
        
        response = self.get_response(request)
        
        return response


class RedirectAuthenticatedMiddleware:
    """
    Middleware para redirigir usuarios autenticados desde login
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si el usuario está autenticado y trata de acceder a login
        if request.user.is_authenticated and request.path == reverse('usuarios:login'):
            return redirect('dashboard:dashboard_principal')
        
        response = self.get_response(request)
        return response


def get_client_ip(request):
    """Obtiene la IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def registrar_acceso(request, accion):
    """
    Registra un acceso en el historial
    """
    if request.user.is_authenticated:
        try:
            HistorialAcceso.objects.create(
                usuario=request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                accion=accion
            )
        except Exception:
            pass  # No fallar si no se puede registrar