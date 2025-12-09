# apps/dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, fields
from django.utils import timezone
from datetime import timedelta, date
from django.conf import settings

from apps.aprendices.models import Aprendiz
from apps.fichas.models import Ficha
from apps.inasistencias.models import Inasistencia
from apps.evaluaciones.models import JuicioEvaluativo
from django.http import HttpResponse


@login_required
def dashboard_principal(request, tipo=None):
    """
    Dashboard principal con métricas de Circular 120
    """
    
    # ============= CASO 1: APRENDICES EN RIESGO DE DESERCIÓN =============
    # Según Circular 120 Tabla 1 Caso 1:
    # Aprendices que superan 18 meses después de etapa lectiva sin definir modalidad productiva
    
    dias_limite_productiva = settings.CIRCULAR_120['DIAS_DEFINIR_MODALIDAD_PRODUCTIVA']
    fecha_limite_productiva = timezone.now().date() - timedelta(days=dias_limite_productiva)
    
    aprendices_riesgo_desercion = Aprendiz.objects.filter(
        estado_formacion__in=['EN_FORMACION', 'CONDICIONADO', 'APLAZADO', 'REINGRESADO'],
        ficha__fecha_fin_lectiva__lt=fecha_limite_productiva,
        activo=True
    ).select_related('ficha', 'ficha__programa').order_by('ficha__fecha_fin_lectiva')
    
    # ============= CASO 2: APRENDICES POR VENCIMIENTO (Próximos 90 días) =============
    fecha_alerta_90_dias = timezone.now().date() + timedelta(days=90)
    fecha_productiva_min = timezone.now().date() - timedelta(days=dias_limite_productiva - 90)
    
    aprendices_proximos_vencer = Aprendiz.objects.filter(
        estado_formacion__in=['EN_FORMACION', 'CONDICIONADO'],
        ficha__fecha_fin_lectiva__gte=fecha_productiva_min,
        ficha__fecha_fin_lectiva__lt=fecha_limite_productiva,
        activo=True
    ).select_related('ficha', 'ficha__programa').order_by('ficha__fecha_fin_lectiva')
    
    # ============= CASO 3: APRENDICES POR CERTIFICAR - VIGENCIA VENCIDA =============
    # Según Circular 120 Tabla 2 Caso 3:
    # Aprendices en estado Por Certificar + 1 año después de evaluada etapa productiva
    
    meses_max_certificar = settings.CIRCULAR_120['MESES_MAXIMOS_POR_CERTIFICAR']
    fecha_limite_certificar = timezone.now().date() - timedelta(days=meses_max_certificar * 30)
    
    aprendices_certificar_vencidos = Aprendiz.objects.filter(
        estado_formacion='POR_CERTIFICAR',
        fecha_actualizacion__lt=fecha_limite_certificar,
        activo=True
    ).select_related('ficha', 'ficha__programa').order_by('fecha_actualizacion')
    
    # ============= CASO 4: APRENDICES CON RAs NO APROBADOS =============
    aprendices_ra_pendientes = Aprendiz.objects.filter(
        activo=True,
        estado_formacion__in=['EN_FORMACION', 'CONDICIONADO']
    ).annotate(
        ra_no_aprobados=Count(
            'juicios_evaluativos',
            filter=Q(juicios_evaluativos__juicio='NO_APROBADO')
        )
    ).filter(ra_no_aprobados__gt=0).select_related('ficha', 'ficha__programa')
    
    # ============= CASO 5: APRENDICES CON BAJO PORCENTAJE DE ASISTENCIA =============
    # Menos del 80% según configuración
    porcentaje_min = settings.CIRCULAR_120['PORCENTAJE_MINIMO_ASISTENCIA']
    
    aprendices_baja_asistencia = []
    aprendices_activos = Aprendiz.objects.filter(
        activo=True,
        estado_formacion__in=['EN_FORMACION', 'CONDICIONADO']
    ).select_related('ficha')
    
    for aprendiz in aprendices_activos:
        porcentaje = aprendiz.porcentaje_asistencia()
        if porcentaje < porcentaje_min:
            aprendices_baja_asistencia.append({
                'aprendiz': aprendiz,
                'porcentaje': porcentaje
            })
    
    # ============= FICHAS VENCIDAS Y PRÓXIMAS A VENCER =============
    fichas_vencidas = Ficha.objects.filter(
        estado='ACTIVA'
    ).annotate(
        dias_vencimiento=ExpressionWrapper(
            (F('fecha_fin_lectiva') + timedelta(days=dias_limite_productiva) - date.today()),
            output_field=fields.DurationField()
        )
    ).filter(dias_vencimiento__lt=timedelta(days=0))
    
    fichas_proximas_vencer = Ficha.objects.filter(
        estado='ACTIVA'
    ).annotate(
        dias_vencimiento=ExpressionWrapper(
            (F('fecha_fin_lectiva') + timedelta(days=dias_limite_productiva) - date.today()),
            output_field=fields.DurationField()
        )
    ).filter(
        dias_vencimiento__gte=timedelta(days=0),
        dias_vencimiento__lte=timedelta(days=90)
    )
    
    # ============= ESTADÍSTICAS GENERALES =============
    total_aprendices = Aprendiz.objects.filter(activo=True).count()
    total_fichas_activas = Ficha.objects.filter(estado='ACTIVA').count()
    
    estadisticas_estados = Aprendiz.objects.filter(activo=True).values(
        'estado_formacion'
    ).annotate(
        total=Count('id')
    ).order_by('-total')
    
    # ============= ACCIONES RECOMENDADAS SEGÚN CIRCULAR 120 =============
    acciones_recomendadas = []
    
    if aprendices_riesgo_desercion.count() > 0:
        acciones_recomendadas.append({
            'prioridad': 'CRÍTICA',
            'cantidad': aprendices_riesgo_desercion.count(),
            'titulo': 'Aprendices en riesgo de deserción',
            'descripcion': 'Aprendices que superaron 18 meses después de etapa lectiva. '
                            'Según Circular 120 Tabla 1 Caso 1, debe declararse deserción.',
            'accion': 'Convocar Comité de Evaluación y Seguimiento para declarar deserción',
            'url': 'dashboard:aprendices_riesgo_desercion'
        })
    
    if aprendices_certificar_vencidos.count() > 0:
        acciones_recomendadas.append({
            'prioridad': 'ALTA',
            'cantidad': aprendices_certificar_vencidos.count(),
            'titulo': 'Aprendices Por Certificar - Vigencia vencida',
            'descripcion': 'Aprendices en estado Por Certificar con más de 1 año desde evaluación. '
                            'Según Circular 120 Tabla 2 Caso 3.',
            'accion': 'Contactar aprendices para traslado de ficha o cancelación',
            'url': 'dashboard:aprendices_certificar_vencidos'
        })
    
    if aprendices_proximos_vencer.count() > 0:
        acciones_recomendadas.append({
            'prioridad': 'MEDIA',
            'cantidad': aprendices_proximos_vencer.count(),
            'titulo': 'Aprendices próximos a vencer (90 días)',
            'descripcion': 'Aprendices que vencen en los próximos 3 meses',
            'accion': 'Realizar seguimiento mensual y definir modalidad de etapa productiva',
            'url': 'dashboard:aprendices_proximos_vencer'
        })
    
    if len(aprendices_baja_asistencia) > 0:
        acciones_recomendadas.append({
            'prioridad': 'MEDIA',
            'cantidad': len(aprendices_baja_asistencia),
            'titulo': f'Aprendices con asistencia menor al {porcentaje_min}%',
            'descripcion': 'Aprendices en riesgo por inasistencias',
            'accion': 'Citación para compromiso académico y mejoramiento',
            'url': 'dashboard:aprendices_baja_asistencia'
        })
    
    if aprendices_ra_pendientes.count() > 0:
        acciones_recomendadas.append({
            'prioridad': 'MEDIA',
            'cantidad': aprendices_ra_pendientes.count(),
            'titulo': 'Aprendices con RAs no aprobados',
            'descripcion': 'Aprendices con resultados de aprendizaje pendientes',
            'accion': 'Plan de mejoramiento y nuevas evaluaciones',
            'url': 'dashboard:aprendices_ra_pendientes'
        })
    
    # Ordenar acciones por prioridad
    prioridad_orden = {'CRÍTICA': 0, 'ALTA': 1, 'MEDIA': 2, 'BAJA': 3}
    acciones_recomendadas.sort(key=lambda x: prioridad_orden[x['prioridad']])
    
    context = {
        'aprendices_riesgo_desercion': aprendices_riesgo_desercion[:10],  # Top 10
        'total_riesgo_desercion': aprendices_riesgo_desercion.count(),
        
        'aprendices_proximos_vencer': aprendices_proximos_vencer[:10],
        'total_proximos_vencer': aprendices_proximos_vencer.count(),
        
        'aprendices_certificar_vencidos': aprendices_certificar_vencidos[:10],
        'total_certificar_vencidos': aprendices_certificar_vencidos.count(),
        
        'aprendices_ra_pendientes': aprendices_ra_pendientes[:10],
        'total_ra_pendientes': aprendices_ra_pendientes.count(),
        
        'aprendices_baja_asistencia': aprendices_baja_asistencia[:10],
        'total_baja_asistencia': len(aprendices_baja_asistencia),
        
        'fichas_vencidas': fichas_vencidas[:10],
        'total_fichas_vencidas': fichas_vencidas.count(),
        
        'fichas_proximas_vencer': fichas_proximas_vencer[:10],
        'total_fichas_proximas': fichas_proximas_vencer.count(),
        
        'total_aprendices': total_aprendices,
        'total_fichas_activas': total_fichas_activas,
        'estadisticas_estados': estadisticas_estados,
        
        'acciones_recomendadas': acciones_recomendadas,
        
        # Configuraciones para mostrar en el dashboard
        'config': {
            'dias_limite_productiva': dias_limite_productiva,
            'meses_limite_productiva': dias_limite_productiva // 30,
            'porcentaje_minimo_asistencia': porcentaje_min,
            'meses_max_certificar': meses_max_certificar,
        }
    }
    
    return render(request, 'dashboard/inicio.html', context)


@login_required
def aprendices_riesgo_desercion(request):
    """Vista detallada de aprendices en riesgo de deserción (Caso 1)"""
    dias_limite = settings.CIRCULAR_120['DIAS_DEFINIR_MODALIDAD_PRODUCTIVA']
    fecha_limite = timezone.now().date() - timedelta(days=dias_limite)
    
    aprendices = Aprendiz.objects.filter(
        estado_formacion__in=['EN_FORMACION', 'CONDICIONADO', 'APLAZADO', 'REINGRESADO'],
        ficha__fecha_fin_lectiva__lt=fecha_limite,
        activo=True
    ).select_related('ficha', 'ficha__programa').order_by('ficha__fecha_fin_lectiva')
    
    context = {
        'aprendices': aprendices,
        'caso_circular': 'Caso 1 - Tabla 1',
        'titulo': 'Aprendices en Riesgo de Deserción',
        'descripcion': f'Aprendices que superaron {dias_limite // 30} meses después de finalizada la etapa lectiva sin definir modalidad de etapa productiva.',
        'accion_sugerida': 'Convocar Comité de Evaluación y Seguimiento para declarar deserción según Reglamento del Aprendiz (Acuerdo 00007 de 2012, Artículo 22 Numeral 4 literal d).',
    }
    
    return render(request, 'dashboard/detalle_caso.html', context)


@login_required
def aprendices_certificar_vencidos(request):
    """Vista detallada de aprendices Por Certificar con vigencia vencida (Caso 3)"""
    meses_max = settings.CIRCULAR_120['MESES_MAXIMOS_POR_CERTIFICAR']
    fecha_limite = timezone.now().date() - timedelta(days=meses_max * 30)
    
    aprendices = Aprendiz.objects.filter(
        estado_formacion='POR_CERTIFICAR',
        fecha_actualizacion__lt=fecha_limite,
        activo=True
    ).select_related('ficha', 'ficha__programa').order_by('fecha_actualizacion')
    
    context = {
        'aprendices': aprendices,
        'caso_circular': 'Caso 3 - Tabla 2',
        'titulo': 'Aprendices Por Certificar - Vigencia Vencida',
        'descripcion': f'Aprendices en estado Por Certificar con más de {meses_max} meses desde la evaluación de etapa productiva.',
        'accion_sugerida': 'Informar al aprendiz mediante correo electrónico para solicitar traslado a ficha en ejecución o retiro voluntario.',
    }
    
    return render(request, 'dashboard/detalle_caso.html', context)

def aprendices_proximos_vencer(request):
    return HttpResponse("Vista de aprendices próximos a vencer")

def aprendices_baja_asistencia(request):
    return HttpResponse("Vista de aprendices con baja asistencia")

def aprendices_ra_pendientes(request):
    return HttpResponse("Vista de aprendices con RAs pendientes")

