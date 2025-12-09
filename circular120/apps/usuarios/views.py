from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash


@login_required
def perfil_usuario(request):
    return render(request, 'usuarios/perfil.html')


@login_required
def cambiar_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Mantiene la sesión activa
            messages.success(request, 'Tu contraseña fue actualizada correctamente.')
            return redirect('usuarios:perfil')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'usuarios/cambiar_password.html', {
        'form': form
    })
