from django.shortcuts import render, redirect, get_object_or_404
from .models import Competencia, ResultadoAprendizaje


# ✅ Listar competencias
def listar_competencias(request):
    competencias = Competencia.objects.all()
    return render(request, 'competencias/lista.html', {
        'competencias': competencias
    })


# ✅ Crear competencia
def crear_competencia(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        Competencia.objects.create(nombre=nombre)
        return redirect('competencias:listar')

    return render(request, 'competencias/crear.html')


# ✅ Detalle de una competencia
def detalle_competencia(request, pk):
    competencia = get_object_or_404(Competencia, pk=pk)
    return render(request, 'competencias/detalle.html', {
        'competencia': competencia
    })


# ✅ Listar resultados de aprendizaje
def listar_resultados_aprendizaje(request):
    resultados = ResultadoAprendizaje.objects.all()
    return render(request, 'competencias/listar_ra.html', {
        'resultados': resultados
    })


# ✅ Crear resultado de aprendizaje
def crear_resultado_aprendizaje(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        ResultadoAprendizaje.objects.create(nombre=nombre)
        return redirect('competencias:listar_ra')

    return render(request, 'competencias/crear_ra.html')
