# aprendices/views.py
import os
from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.core.management import call_command
from .models import Aprendiz, Ficha, Inasistencia, Competencia, ResultadoAprendizaje, AprendizResultado, ActaComite
from .forms import AprendizForm, InasistenciaForm, UploadFileForm

# ============================================
# DASHBOARD CON LÓGICA CIRCULAR 120
# ============================================
@login_required
def dashboard(request):
    hoy = timezone.now().date()

    # Estadísticas generales
    total_aprendices = Aprendiz.objects.count()
    total_fichas = Ficha.objects.count()
    total_inasistencias = Inasistencia.objects.count()

    # ✅ Aprendices por certificar (estado específico)
    por_certificar = Aprendiz.objects.filter(estado_formacion='POR_CERTIFICAR')

    # ✅ Aprendices con etapa productiva vencida (más de 18 meses o fecha pasada)
    productiva_vencida = Aprendiz.objects.filter(
        estado_formacion='ETAPA_PRODUCTIVA',
        fecha_fin_productiva__lt=hoy
    )

    # ✅ Aprendices con ficha finalizada pero NO certificados
    ficha_vencida = Aprendiz.objects.filter(
        ficha__fecha_fin__lt=hoy
    ).exclude(estado_formacion='CERTIFICADO')

    # ✅ Casos urgentes (vencidos por más de 30 días)
    casos_urgentes = Aprendiz.objects.filter(
        Q(ficha__fecha_fin__lt=hoy - timedelta(days=30)) |
        Q(fecha_fin_productiva__lt=hoy - timedelta(days=30))
    ).exclude(estado_formacion='CERTIFICADO').exclude(estado_formacion='CANCELADO')

    # Distribución por estado
    por_estado = Aprendiz.objects.values('estado_formacion').annotate(total=Count('documento'))

    context = {
        'total_aprendices': total_aprendices,
        'total_fichas': total_fichas,
        'total_inasistencias': total_inasistencias,
        'por_certificar': por_certificar.count(),
        'productiva_vencida': productiva_vencida.count(),
        'ficha_vencida': ficha_vencida.count(),
        'casos_urgentes': casos_urgentes.count(),
        'por_estado': por_estado,
        'lista_urgentes': casos_urgentes[:10],  # Primeros 10 para mostrar
    }
    
    return render(request, 'aprendices/dashboard.html', context)


# ============================================
# CASOS POR CERTIFICAR
# ============================================
@login_required
def casos_por_certificar(request):
    aprendices = Aprendiz.objects.filter(
        estado_formacion='POR_CERTIFICAR'
    ).select_related('ficha').order_by('fecha_fin_productiva')
    
    return render(request, 'aprendices/casos_por_certificar.html', {
        'aprendices': aprendices,
        'total': aprendices.count()
    })


# ============================================
# CASOS VENCIDOS
# ============================================
@login_required
def casos_vencidos(request):
    hoy = timezone.now().date()
    
    # Aprendices con ficha vencida o productiva vencida
    aprendices_vencidos = Aprendiz.objects.filter(
        Q(ficha__fecha_fin__lt=hoy) |
        Q(fecha_fin_productiva__lt=hoy)
    ).exclude(estado_formacion='CERTIFICADO').exclude(estado_formacion='CANCELADO').select_related('ficha')
    
    # Clasificar por nivel de urgencia
    urgentes = []
    moderados = []
    recientes = []
    
    for aprendiz in aprendices_vencidos:
        dias = aprendiz.dias_vencido()
        if dias > 60:
            urgentes.append(aprendiz)
        elif dias > 30:
            moderados.append(aprendiz)
        else:
            recientes.append(aprendiz)
    
    return render(request, 'aprendices/casos_vencidos.html', {
        'urgentes': urgentes,
        'moderados': moderados,
        'recientes': recientes,
        'total': len(urgentes) + len(moderados) + len(recientes)
    })


# ============================================
# REPORTE CIRCULAR 120
# ============================================
@login_required
def reporte_circular120(request):
    hoy = timezone.now().date()
    
    # Todos los casos relevantes para el comité
    por_certificar = Aprendiz.objects.filter(estado_formacion='POR_CERTIFICAR')
    productiva_vencida = Aprendiz.objects.filter(
        estado_formacion='ETAPA_PRODUCTIVA',
        fecha_fin_productiva__lt=hoy
    )
    ficha_vencida = Aprendiz.objects.filter(
        ficha__fecha_fin__lt=hoy
    ).exclude(estado_formacion='CERTIFICADO')
    
    return render(request, 'aprendices/reporte_circular120.html', {
        'por_certificar': por_certificar,
        'productiva_vencida': productiva_vencida,
        'ficha_vencida': ficha_vencida,
        'fecha_generacion': hoy,
    })


# ============================================
# ACCIONES SOBRE APRENDICES
# ============================================
@login_required
def aprobar_certificacion(request, documento):
    aprendiz = get_object_or_404(Aprendiz, documento=documento)
    aprendiz.estado_formacion = 'CERTIFICADO'
    aprendiz.save()
    messages.success(request, f'Aprendiz {aprendiz.nombre} {aprendiz.apellido} marcado como CERTIFICADO')
    return redirect('casos_por_certificar')


@login_required
def cancelar_aprendiz(request, documento):
    aprendiz = get_object_or_404(Aprendiz, documento=documento)
    aprendiz.estado_formacion = 'CANCELADO'
    aprendiz.save()
    messages.warning(request, f'Aprendiz {aprendiz.nombre} {aprendiz.apellido} marcado como CANCELADO')
    return redirect('casos_vencidos')


# ============================================
# CRUD APRENDIZ (ya existentes, mantenidos)
# ============================================
class AprendizListView(LoginRequiredMixin, ListView):
    model = Aprendiz
    template_name = 'aprendices/aprendiz_list.html'
    paginate_by = 50
    ordering = ['-created_at']

class AprendizCreateView(LoginRequiredMixin, CreateView):
    model = Aprendiz
    form_class = AprendizForm
    template_name = 'aprendices/aprendiz_form.html'
    success_url = reverse_lazy('aprendiz_list')

class AprendizUpdateView(LoginRequiredMixin, UpdateView):
    model = Aprendiz
    form_class = AprendizForm
    template_name = 'aprendices/aprendiz_form.html'
    success_url = reverse_lazy('aprendiz_list')

class AprendizDetailView(LoginRequiredMixin, DetailView):
    model = Aprendiz
    template_name = 'aprendices/aprendiz_detail.html'

# ============================================
# INASISTENCIAS
# ============================================
class InasistenciaCreateView(LoginRequiredMixin, CreateView):
    model = Inasistencia
    form_class = InasistenciaForm
    template_name = 'aprendices/inasistencia_form.html'
    success_url = reverse_lazy('inasistencia_list')

class InasistenciaListView(LoginRequiredMixin, ListView):
    model = Inasistencia
    template_name = 'aprendices/inasistencia_list.html'
    paginate_by = 50
    ordering = ['-fecha']

# ============================================
# ACTAS DE COMITÉ
# ============================================
class ActaCreateView(LoginRequiredMixin, CreateView):
    model = ActaComite
    fields = ['ficha','fecha','contenido','archivo_pdf','creado_por']
    template_name = 'aprendices/acta_form.html'
    success_url = reverse_lazy('dashboard')

# ============================================
# UPLOAD DE ARCHIVOS EXCEL
# ============================================
class FileUploadView(LoginRequiredMixin, View):
    template_name = 'aprendices/upload_file.html'
    form_class = UploadFileForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['file']
            tmp_dir = getattr(settings, 'MEDIA_ROOT', None) or '/tmp'
            tmp_subdir = os.path.join(tmp_dir, 'temp_uploads')
            os.makedirs(tmp_subdir, exist_ok=True)
            tmp_path = os.path.join(tmp_subdir, f.name)
            with open(tmp_path, 'wb') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)
            try:
                call_command('import_consolidado', tmp_path)
                messages.success(request, f'Archivo {f.name} procesado correctamente.')
            except Exception as e:
                messages.error(request, f'Error procesando archivo: {e}')
            return redirect('upload_file')
        return render(request, self.template_name, {'form': form})


# Crear una clase-based view para el dashboard también
class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        return dashboard(request)