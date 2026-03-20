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
    
    # Filtros opcionales
    ficha_id = request.GET.get('ficha')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    ficha = None
    if ficha_id:
        ficha = Ficha.objects.filter(numero=ficha_id).first()
    
    # Generar Excel
    excel_file = generador.generar_reporte_inasistencias(
        ficha=ficha,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta
    )
    
    # Preparar respuesta
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
        
        # Contar reportes exitosos
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


# ==========================================
# VISTA DE UPLOAD CON FECHAS MANUALES
# ==========================================

class FileUploadView(LoginRequiredMixin, View):
    template_name = 'aprendices/upload_file.html'
    form_class = UploadFileWithDatesForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            f = form.cleaned_data['file']
            
            # Obtener datos manuales del formulario
            ficha_manual = form.cleaned_data.get('ficha_manual')
            programa_manual = form.cleaned_data.get('programa_manual')
            fecha_inicio = form.cleaned_data.get('fecha_inicio_manual')
            fecha_fin = form.cleaned_data.get('fecha_fin_manual')
            
            # Guardar archivo temporal
            tmp_dir = getattr(settings, 'MEDIA_ROOT', None) or '/tmp'
            tmp_subdir = os.path.join(tmp_dir, 'temp_uploads')
            os.makedirs(tmp_subdir, exist_ok=True)
            tmp_path = os.path.join(tmp_subdir, f.name)
            
            with open(tmp_path, 'wb') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)
            
            try:
                # Ejecutar comando de importación
                call_command('import_consolidado', tmp_path)
                
                # Si hay fechas manuales, actualizar (con o sin ficha manual)
                if fecha_inicio or fecha_fin or (ficha_manual and programa_manual):
                    print("DEBUG: Entrando al bloque de actualización...")
                    try:
                        # Determinar qué ficha usar
                        if ficha_manual:
                            ficha_numero = ficha_manual
                        else:
                            # Usar la última ficha creada/modificada (la del archivo actual)
                            ultima_ficha = Ficha.objects.order_by('-id').first()
                            if ultima_ficha:
                                ficha_numero = ultima_ficha.numero
                            else:
                                raise Exception("No se encontró ninguna ficha")
                        
                        print(f"DEBUG: Buscando ficha {ficha_numero}...")
                        
                        # Buscar o crear la ficha
                        ficha_obj, created = Ficha.objects.get_or_create(
                            numero=ficha_numero,
                            defaults={'programa': programa_manual or 'Por definir'}
                        )
                        
                        print(f"DEBUG: Ficha encontrada: {ficha_obj.numero}, Programa actual: {ficha_obj.programa}")
                        
                        # Actualizar ficha con datos manuales
                        cambios_ficha = False
                        if programa_manual and (not ficha_obj.programa or ficha_obj.programa == 'Por definir'):
                            ficha_obj.programa = programa_manual
                            cambios_ficha = True
                        if fecha_inicio and not ficha_obj.fecha_inicio:
                            ficha_obj.fecha_inicio = fecha_inicio
                            cambios_ficha = True
                        if fecha_fin and not ficha_obj.fecha_fin:
                            ficha_obj.fecha_fin = fecha_fin
                            cambios_ficha = True
                        
                        if cambios_ficha:
                            ficha_obj.save()
                            print(f"DEBUG: Ficha actualizada con programa: {ficha_obj.programa}")
                        
                        # Actualizar TODOS los aprendices de esa ficha con las fechas ingresadas
                        aprendices = Aprendiz.objects.filter(ficha=ficha_obj)
                        print(f"DEBUG: Encontrados {aprendices.count()} aprendices en la ficha")
                        actualizados = 0
                        
                        for aprendiz in aprendices:
                            cambios = False
                            # SIEMPRE actualizar si se ingresó fecha manual
                            if fecha_inicio:
                                aprendiz.fecha_inicio = fecha_inicio
                                cambios = True
                            if fecha_fin:
                                aprendiz.fecha_final = fecha_fin
                                cambios = True
                                
                                # CALCULAR AUTOMÁTICAMENTE las fechas de etapas
                                # Etapa productiva = 6 meses antes de la fecha fin
                                from dateutil.relativedelta import relativedelta
                                aprendiz.fecha_fin_lectiva = fecha_fin - relativedelta(months=6)
                                aprendiz.fecha_fin_productiva = fecha_fin
                            
                            if cambios:
                                aprendiz.save()
                                actualizados += 1
                        
                        print(f"DEBUG: {actualizados} aprendices actualizados")
                        
                        if actualizados > 0:
                            msg = f'✅ {actualizados} aprendices actualizados.'
                            if fecha_inicio:
                                msg += f' Fecha Inicio: {fecha_inicio.strftime("%d/%m/%Y")}'
                            if fecha_fin:
                                msg += f' | Fecha Fin: {fecha_fin.strftime("%d/%m/%Y")}'
                            messages.success(request, msg)
                        else:
                            messages.success(request, f'✅ Archivo {f.name} procesado correctamente.')
                    
                    except Ficha.DoesNotExist:
                        messages.warning(request, f'⚠️ No se encontró la ficha para actualizar fechas.')
                    except Exception as e:
                        messages.warning(request, f'⚠️ Error: {e}')
                else:
                    messages.success(request, f'✅ Archivo {f.name} procesado correctamente.')
                
            except Exception as e:
                messages.error(request, f'❌ Error procesando archivo: {e}')
            
            # Limpiar archivo temporal
            try:
                os.remove(tmp_path)
            except:
                pass
                
            return redirect('aprendiz_list')
        
        return render(request, self.template_name, {'form': form})