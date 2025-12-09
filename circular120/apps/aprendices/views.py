from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Aprendiz
from django.contrib.auth.decorators import login_required


@login_required
def lista_aprendices(request):
    aprendices = Aprendiz.objects.all()
    return render(request, 'aprendices/lista.html', {
        'aprendices': aprendices
    })


@login_required
def crear_aprendiz(request):
    return HttpResponse("Vista para crear aprendiz")


@login_required
def detalle_aprendiz(request, pk):
    aprendiz = get_object_or_404(Aprendiz, pk=pk)
    return HttpResponse(f"Detalle del aprendiz: {aprendiz}")


@login_required
def editar_aprendiz(request, pk):
    aprendiz = get_object_or_404(Aprendiz, pk=pk)
    return HttpResponse(f"Editar aprendiz: {aprendiz}")


@login_required
def historial_aprendiz(request, pk):
    aprendiz = get_object_or_404(Aprendiz, pk=pk)
    return HttpResponse(f"Historial del aprendiz: {aprendiz}")


@login_required
def buscar_aprendiz(request):
    return HttpResponse("Buscar aprendiz")
