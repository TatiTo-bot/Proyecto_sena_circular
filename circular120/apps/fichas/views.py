from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Ficha


@login_required
def listar_fichas(request):
    fichas = Ficha.objects.all()
    return HttpResponse("Listado de fichas")


@login_required
def crear_ficha(request):
    return HttpResponse("Crear ficha")


@login_required
def detalle_ficha(request, pk):
    ficha = get_object_or_404(Ficha, pk=pk)
    return HttpResponse(f"Detalle de ficha {ficha}")


@login_required
def aprendices_ficha(request, pk):
    ficha = get_object_or_404(Ficha, pk=pk)
    return HttpResponse(f"Aprendices de la ficha {ficha}")


@login_required
def fichas_vencidas(request):
    return HttpResponse("Listado de fichas vencidas")


@login_required
def fichas_alertas(request):
    return HttpResponse("Alertas de fichas")
