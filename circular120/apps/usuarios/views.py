from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.contrib.auth import update_session_auth_hash
from apps.usuarios.middleware import registrar_acceso

def login_view(request):
    """Vista personalizada de login con registro de acceso"""
    # Si ya está autenticado, redirigir al dashboard
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard_principal')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            
            # Registrar acceso exitoso
            registrar_acceso(request, 'LOGIN')
            
            messages.success(
                request, 
                f'¡Bienvenido, {user.get_full_name() or user.username}!'
            )
            
            # Redirigir a la página solicitada o al dashboard
            next_url = request.GET.get('next', 'dashboard:dashboard_principal')
            return redirect(next_url)
        else:
            # Registrar intento fallido
            if username:
                try:
                    from django.contrib.auth.models import User
                    from apps.usuarios.models import HistorialAcceso
                    from apps.usuarios.middleware import get_client_ip
                    
                    user_obj = User.objects.filter(username=username).first()
                    if user_obj:
                        HistorialAcceso.objects.create(
                            usuario=user_obj,
                            ip_address=get_client_ip(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                            accion='FAILED_LOGIN'
                        )
                except:
                    pass
            
            messages.error(request, '❌ Usuario o contraseña incorrectos')
    else:
        form = AuthenticationForm()
    
    return render(request, 'usuarios/login.html', {'form': form})


@login_required
def logout_view(request):
    """Vista personalizada de logout con registro"""
    # Registrar cierre de sesión
    registrar_acceso(request, 'LOGOUT')
    
    username = request.user.get_full_name() or request.user.username
    
    auth_logout(request)
    
    messages.info(request, f'Has cerrado sesión correctamente. ¡Hasta pronto, {username}!')
    
    return redirect('usuarios:login')


@login_required
def perfil_usuario(request):
    """Vista del perfil del usuario"""
    perfil = getattr(request.user, 'perfil', None)
    
    # Obtener últimos accesos
    ultimos_accesos = request.user.historial_accesos.all()[:10]
    
    # Obtener estadísticas si es instructor
    fichas_asignadas = []
    if perfil and perfil.es_instructor():
        from apps.fichas.models import Ficha
        fichas_asignadas = Ficha.objects.filter(
            instructor_lider=request.user,
            estado='ACTIVA'
        ).select_related('programa')
    
    context = {
        'perfil': perfil,
        'ultimos_accesos': ultimos_accesos,
        'fichas_asignadas': fichas_asignadas,
    }
    
    return render(request, 'usuarios/perfil.html', context)


@login_required
def cambiar_password(request):
    """Cambio de contraseña"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            
            # Registrar cambio de contraseña
            registrar_acceso(request, 'PASSWORD_CHANGE')
            
            messages.success(request, '✅ Tu contraseña fue actualizada correctamente.')
            return redirect('usuarios:perfil')
        else:
            messages.error(request, '❌ Por favor corrige los errores.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'usuarios/cambiar-password.html', {'form': form})