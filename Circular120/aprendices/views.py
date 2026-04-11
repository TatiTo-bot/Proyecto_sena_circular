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
from .forms import AprendizForm, InasistenciaForm, UploadFileForm, UploadFileWithDatesForm
from django.http import HttpResponse, FileResponse
from aprendices.utils.reportes import GeneradorReportes, generar_todos_reportes
import mimetypes

@login_required
def dashboard(request):
    hoy = timezone.now().date()

    total_aprendices = Aprendiz.objects.count()
    total_fichas = Ficha.objects.count()
    total_inasistencias = Inasistencia.objects.count()

    por_certificar = Aprendiz.objects.filter(estado_formacion='POR_CERTIFICAR')

    productiva_vencida = Aprendiz.objects.filter(
        estado_formacion='ETAPA_PRODUCTIVA',
        fecha_fin_productiva__lt=hoy
    )

    ficha_vencida = Aprendiz.objects.filter(
        ficha__fecha_fin__lt=hoy
    ).exclude(estado_formacion='CERTIFICADO')

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


@login_required
def casos_por_certificar(request):
    aprendices = Aprendiz.objects.filter(
        estado_formacion='POR_CERTIFICAR'
    ).select_related('ficha').order_by('fecha_fin_productiva')
    
    return render(request, 'aprendices/casos_por_certificar.html', {
        'aprendices': aprendices,
        'total': aprendices.count()
    })


@login_required
def casos_vencidos(request):
    hoy = timezone.now().date()

    aprendices_vencidos = Aprendiz.objects.filter(
        estado_formacion='EN_FORMACION'          
    ).filter(
        Q(ficha__fecha_fin__lt=hoy) |
        Q(fecha_fin_productiva__lt=hoy)
    ).select_related('ficha')

    urgentes  = []
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
        'urgentes':  urgentes,
        'moderados': moderados,
        'recientes': recientes,
        'total': len(urgentes) + len(moderados) + len(recientes)
    })

@login_required
def reporte_circular120(request):
    hoy = timezone.now().date()

    por_certificar = Aprendiz.objects.filter(
        estado_formacion='POR_CERTIFICAR'
    ).select_related('ficha')

    productiva_vencida = Aprendiz.objects.filter(
        estado_formacion='ETAPA_PRODUCTIVA',
        fecha_fin_productiva__lt=hoy
    ).select_related('ficha')

    ficha_vencida = Aprendiz.objects.filter(
        ficha__fecha_fin__lt=hoy,
        estado_formacion='EN_FORMACION'          
    ).select_related('ficha')

    return render(request, 'aprendices/reporte_circular120.html', {
        'por_certificar':     por_certificar,
        'productiva_vencida': productiva_vencida,
        'ficha_vencida':      ficha_vencida,
        'fecha_generacion':   hoy,
    })

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


class AprendizListView(LoginRequiredMixin, ListView):
    model = Aprendiz
    template_name = 'aprendices/aprendiz_list.html'
    paginate_by = 50
    ordering = ['-created_at']
    
    def get_queryset(self):
        qs = Aprendiz.objects.select_related('ficha').annotate(
            juicios_pendientes=Count(
                'juicios',
                filter=Q(juicios__estado='PENDIENTE')
            )
        )

        self.filtro_ficha = self.request.GET.get('ficha', '').strip()
        if self.filtro_ficha:
            qs = qs.filter(ficha__numero=self.filtro_ficha)

        self.filtro_estado = self.request.GET.get('estado', '').strip()
        if self.filtro_estado:
            qs = qs.filter(estado_formacion=self.filtro_estado)

        return qs.order_by('apellido', 'nombre')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['fichas'] = Ficha.objects.order_by('numero')
        ctx['estados'] = Aprendiz.ESTADO_FORMACION_CHOICES
        ctx['filtro_ficha'] = getattr(self, 'filtro_ficha', '')
        ctx['filtro_estado'] = getattr(self, 'filtro_estado', '')
        return ctx
    
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

class ActaCreateView(LoginRequiredMixin, CreateView):
    model = ActaComite
    fields = ['ficha','fecha','contenido','archivo_pdf','creado_por']
    template_name = 'aprendices/acta_form.html'
    success_url = reverse_lazy('dashboard')


class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        return dashboard(request)
    
@login_required
def descargar_reporte_inasistencias(request):
    """Genera y descarga reporte de inasistencias en Excel"""
    generador = GeneradorReportes()
    
    ficha_id = request.GET.get('ficha')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    ficha = None
    if ficha_id:
        ficha = Ficha.objects.filter(numero=ficha_id).first()
    
    excel_file = generador.generar_reporte_inasistencias(
        ficha=ficha,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta
    )
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'reporte_inasistencias_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    messages.success(request, f'Reporte de inasistencias generado: {filename}')
    return response

@login_required
def descargar_reporte_juicios(request):
    """Genera y descarga reporte de juicios evaluativos en Excel"""
    generador = GeneradorReportes()
    
    ficha_id = request.GET.get('ficha')
    ficha = None
    if ficha_id:
        ficha = Ficha.objects.filter(numero=ficha_id).first()
    
    excel_file = generador.generar_reporte_juicios(ficha=ficha)
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'reporte_juicios_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    messages.success(request, f'Reporte de juicios generado: {filename}')
    return response


@login_required
def descargar_reporte_circular120(request):
    """Genera y descarga reporte Circular 120 completo en Excel"""
    generador = GeneradorReportes()
    excel_file = generador.generar_reporte_circular120()
    
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'reporte_circular120_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    messages.success(request, f'Reporte Circular 120 generado: {filename}')
    return response


@login_required
def generar_todos_reportes_view(request):
    """Genera todos los reportes automáticamente"""
    try:
        reportes = generar_todos_reportes()
        
        exitosos = sum(1 for k, v in reportes.items() if not k.endswith('_error'))
        errores = sum(1 for k in reportes.keys() if k.endswith('_error'))
        
        if exitosos > 0:
            messages.success(
                request,
                f'✅ Se generaron {exitosos} reportes correctamente.'
            )
        
        if errores > 0:
            messages.warning(
                request,
                f'⚠ {errores} reportes tuvieron errores.'
            )
        
    except Exception as e:
        messages.error(request, f'Error generando reportes: {e}')
    
    return redirect('dashboard')

class FileUploadView(LoginRequiredMixin, View):
    template_name = 'aprendices/upload_file.html'
    form_class = UploadFileWithDatesForm
 
    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
 
    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
 
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})
 
        f       = form.cleaned_data['file']
        tipo    = request.POST.get('tipo_archivo', 'juicios')  # 'juicios' o 'inasistencias'
 
        if tipo == 'inasistencias':
            from .views_import import import_inasistencias
            return import_inasistencias(request)
 
        # ── JUICIOS / APRENDICES (flujo original) ─────────────────
        ficha_manual    = form.cleaned_data.get('ficha_manual')
        programa_manual = form.cleaned_data.get('programa_manual')
        fecha_inicio    = form.cleaned_data.get('fecha_inicio_manual')
        fecha_fin       = form.cleaned_data.get('fecha_fin_manual')
 
        tmp_dir    = getattr(settings, 'MEDIA_ROOT', None) or '/tmp'
        tmp_subdir = os.path.join(tmp_dir, 'temp_uploads')
        os.makedirs(tmp_subdir, exist_ok=True)
        tmp_path   = os.path.join(tmp_subdir, f.name)
 
        with open(tmp_path, 'wb') as dest:
            for chunk in f.chunks():
                dest.write(chunk)
 
        try:
            call_command('import_consolidado', tmp_path)
 
            if fecha_inicio or fecha_fin or (ficha_manual and programa_manual):
                try:
                    ficha_numero = ficha_manual
                    if not ficha_numero:
                        ultima = Ficha.objects.order_by('-numero').first()
                        ficha_numero = ultima.numero if ultima else None
 
                    if ficha_numero:
                        ficha_obj, _ = Ficha.objects.get_or_create(
                            numero=ficha_numero,
                            defaults={'programa': programa_manual or 'Por definir'}
                        )
                        if programa_manual and (not ficha_obj.programa or ficha_obj.programa == 'Por definir'):
                            ficha_obj.programa = programa_manual
                            ficha_obj.save()
                        if fecha_inicio and not ficha_obj.fecha_inicio:
                            ficha_obj.fecha_inicio = fecha_inicio
                            ficha_obj.save()
                        if fecha_fin and not ficha_obj.fecha_fin:
                            ficha_obj.fecha_fin = fecha_fin
                            ficha_obj.save()
 
                        from dateutil.relativedelta import relativedelta
                        actualizados = 0
                        for aprendiz in Aprendiz.objects.filter(ficha=ficha_obj):
                            cambios = []
                            if fecha_inicio and not aprendiz.fecha_inicio:
                                aprendiz.fecha_inicio = fecha_inicio
                                cambios.append('fecha_inicio')
                            if fecha_fin:
                                if not aprendiz.fecha_final:
                                    aprendiz.fecha_final = fecha_fin
                                    cambios.append('fecha_final')
                                if not aprendiz.fecha_fin_productiva:
                                    aprendiz.fecha_fin_productiva = fecha_fin
                                    cambios.append('fecha_fin_productiva')
                                if not aprendiz.fecha_fin_lectiva:
                                    aprendiz.fecha_fin_lectiva = fecha_fin - relativedelta(months=6)
                                    cambios.append('fecha_fin_lectiva')
                            if cambios:
                                aprendiz.save(update_fields=cambios)
                                actualizados += 1
 
                        if actualizados:
                            messages.success(request, f'✅ {actualizados} aprendices actualizados con fechas.')
 
                except Exception as e:
                    messages.warning(request, f'⚠️ Error actualizando fechas: {e}')
            else:
                messages.success(request, f'✅ Archivo {f.name} procesado correctamente.')
 
        except Exception as e:
            messages.error(request, f'❌ Error procesando archivo: {e}')
 
        try:
            os.remove(tmp_path)
        except Exception:
            pass
 
        return redirect('aprendiz_list')