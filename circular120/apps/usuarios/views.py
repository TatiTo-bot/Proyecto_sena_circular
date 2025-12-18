# apps/usuarios/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from apps.usuarios.middleware import registrar_acceso
from apps.usuarios.models import PerfilUsuario


def login_view(request):
    """Vista personalizada de login con validaciones"""
    # Si ya está autenticado, redirigir
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard_principal')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Validar campos vacíos
        if not username:
            messages.error(request, '❌ Por favor ingresa tu usuario')
            return render(request, 'usuarios/login.html')
        
        if not password:
            messages.error(request, '❌ Por favor ingresa tu contraseña')
            return render(request, 'usuarios/login.html')
        
        # Autenticar
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Login exitoso
            auth_login(request, user)
            
            # Registrar acceso
            try:
                registrar_acceso(request, 'LOGIN')
            except:
                pass
            
            messages.success(
                request, 
                f'✅ ¡Bienvenido, {user.get_full_name() or user.username}!'
            )
            
            # Redirigir
            next_url = request.GET.get('next', 'dashboard:dashboard_principal')
            return redirect(next_url)
        else:
            # Login fallido
            # Verificar si el usuario existe
            user_exists = User.objects.filter(username=username).exists()
            
            if user_exists:
                messages.error(request, '❌ Contraseña incorrecta. Intenta nuevamente.')
            else:
                messages.error(request, '❌ Usuario no encontrado. Verifica tu nombre de usuario.')
            
            # Registrar intento fallido
            try:
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
    
    return render(request, 'usuarios/login.html')


def registro_view(request):
    """Vista para registrar nuevos usuarios"""
    if request.method == 'POST':
        # Obtener datos del formulario
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        documento = request.POST.get('documento', '').strip()
        rol = request.POST.get('rol', 'INSTRUCTOR')
        
        # Validaciones
        errores = []
        
        if not username:
            errores.append('El usuario es obligatorio')
        elif User.objects.filter(username=username).exists():
            errores.append('Este usuario ya existe')
        
        if not email:
            errores.append('El email es obligatorio')
        elif not email.endswith(('@sena.edu.co', '@misena.edu.co')):
            errores.append('Debes usar un correo institucional SENA')
        elif User.objects.filter(email=email).exists():
            errores.append('Este email ya está registrado')
        
        if not password1:
            errores.append('La contraseña es obligatoria')
        elif len(password1) < 8:
            errores.append('La contraseña debe tener al menos 8 caracteres')
        
        if password1 != password2:
            errores.append('Las contraseñas no coinciden')
        
        if not documento:
            errores.append('El documento es obligatorio')
        elif PerfilUsuario.objects.filter(documento=documento).exists():
            errores.append('Este documento ya está registrado')
        
        if errores:
            for error in errores:
                messages.error(request, f'❌ {error}')
            return render(request, 'usuarios/registro.html', {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'documento': documento,
            })
        
        # Crear usuario
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            
            # Actualizar perfil
            perfil = user.perfil
            perfil.documento = documento
            perfil.rol = rol
            perfil.save()
            
            messages.success(request, '✅ Usuario creado exitosamente. Ya puedes iniciar sesión.')
            return redirect('usuarios:login')
            
        except Exception as e:
            messages.error(request, f'❌ Error al crear usuario: {str(e)}')
            return render(request, 'usuarios/registro.html')
    
    return render(request, 'usuarios/registro.html')


@login_required
def logout_view(request):
    """Vista de logout"""
    try:
        registrar_acceso(request, 'LOGOUT')
    except:
        pass
    
    username = request.user.get_full_name() or request.user.username
    auth_logout(request)
    messages.info(request, f'👋 Has cerrado sesión. ¡Hasta pronto, {username}!')
    return redirect('usuarios:login')


@login_required
def perfil_usuario(request):
    """Vista del perfil"""
    perfil = getattr(request.user, 'perfil', None)
    ultimos_accesos = request.user.historial_accesos.all()[:10]
    
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
            
            try:
                registrar_acceso(request, 'PASSWORD_CHANGE')
            except:
                pass
            
            messages.success(request, '✅ Contraseña actualizada correctamente.')
            return redirect('usuarios:perfil')
        else:
            for error in form.errors.values():
                messages.error(request, f'❌ {error}')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'usuarios/cambiar-password.html', {'form': form})