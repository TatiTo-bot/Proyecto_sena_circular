# aprendices/views.py
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib import messages
from django.core.management import call_command
from .models import Aprendiz, Ficha, Inasistencia, Competencia, ResultadoAprendizaje, AprendizResultado, ActaComite
from .forms import AprendizForm, InasistenciaForm, UploadFileForm

# CRUD Aprendiz
class AprendizListView(LoginRequiredMixin, ListView):
    model = Aprendiz
    template_name = 'aprendices/aprendiz_list.html'
    paginate_by = 50

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

# Inasistencias
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

# Dashboard de depuración
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'aprendices/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoy = timezone.now().date()

        por_estado = Aprendiz.objects.values('estado_formacion').annotate(total=Count('documento'))

        aprendices_vencidos = Aprendiz.objects.filter(ficha__fecha_fin__lt=hoy).select_related('ficha')

        vencidos_complementaria = []
        vencidos_titulada = []
        for a in aprendices_vencidos:
            if a.ficha and a.ficha.fecha_fin:
                dias = (hoy - a.ficha.fecha_fin).days
                if dias > 90:  # complementaria > 3 meses
                    vencidos_complementaria.append(a)
                if dias > 365:  # ejemplo regla para titulada (ajustar)
                    vencidos_titulada.append(a)

        ctx.update({
            'por_estado': por_estado,
            'vencidos_count': aprendices_vencidos.count(),
            'vencidos_list': aprendices_vencidos[:200],
            'vencidos_complementaria_count': len(vencidos_complementaria),
            'vencidos_titulada_count': len(vencidos_titulada),
        })
        return ctx

# Acta
class ActaCreateView(LoginRequiredMixin, CreateView):
    model = ActaComite
    fields = ['ficha','fecha','contenido','archivo_pdf','creado_por']
    template_name = 'aprendices/acta_form.html'
    success_url = reverse_lazy('dashboard')

# File upload view (subir Excel desde web y ejecutar import)
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
                # llamar al management command para procesar
                call_command('import_consolidado', tmp_path)
                messages.success(request, f'Archivo {f.name} procesado correctamente.')
            except Exception as e:
                messages.error(request, f'Error procesando archivo: {e}')
            return redirect('upload_file')
        return render(request, self.template_name, {'form': form})
