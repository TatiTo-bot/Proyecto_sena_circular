from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """
    Decorador para verificar que el usuario tenga uno de los roles especificados
    Uso: @role_required('Administrador', 'Instructor')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('usuarios:login')
            
            # Superusuarios tienen acceso total
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Verificar si el usuario tiene alguno de los roles requeridos
            user_groups = request.user.groups.values_list('name', flat=True)
            
            if any(role in user_groups for role in roles):
                return view_func(request, *args, **kwargs)
            
            messages.error(request, 'No tienes permisos para acceder a esta página.')
            return redirect('dashboard:dashboard_principal')
        
        return wrapped_view
    return decorator


def instructor_required(view_func):
    """Decorador para vistas que requieren rol de Instructor"""
    return role_required('Instructor', 'Administrador')(view_func)


def administrador_required(view_func):
    """Decorador para vistas que requieren rol de Administrador"""
    return role_required('Administrador')(view_func)


def coordinador_required(view_func):
    """Decorador para vistas que requieren rol de Coordinador"""
    return role_required('Coordinador', 'Administrador')(view_func)


def consulta_only(view_func):
    """Decorador para vistas de solo lectura"""
    return role_required('Consulta', 'Instructor', 'Coordinador', 'Administrador')(view_func)