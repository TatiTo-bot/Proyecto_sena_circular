# apps/alertas/tasks.py
from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from apps.fichas.models import Ficha
from apps.aprendices.models import Aprendiz
from apps.inasistencias.models import Inasistencia
from apps.evaluaciones.models import JuicioEvaluativo

logger = logging.getLogger('alertas')


@shared_task
def enviar_alerta_fichas_proximas_vencer():
    """
    Envía alertas a instructores de fichas que están próximas a vencer
    (90 días antes del vencimiento según Circular 120)
    """
    dias_limite = settings.CIRCULAR_120['DIAS_DEFINIR_MODALIDAD_PRODUCTIVA']
    fecha_alerta = timezone.now().date() + timedelta(days=90)
    fecha_min = timezone.now().date() - timedelta(days=dias_limite - 90)
    
    fichas_alerta = Ficha.objects.filter(
        estado='ACTIVA',
        fecha_fin_lectiva__gte=fecha_min,
        fecha_fin_lectiva__lt=fecha_alerta,
        instructor_lider__isnull=False
    ).select_related('instructor_lider', 'programa')
    
    emails_enviados = 0
    
    for ficha in fichas_alerta:
        try:
            # Contar aprendices activos en la ficha
            aprendices_activos = ficha.aprendices.filter(
                activo=True,
                estado_formacion__in=['EN_FORMACION', 'CONDICIONADO']
            ).count()
            
            if aprendices_activos == 0:
                continue
            
            dias_restantes = ficha.dias_para_vencimiento_certificacion()
            
            # Preparar email
            subject = f'⚠️ ALERTA: Ficha {ficha.numero} próxima a vencer ({dias_restantes} días)'
            
            context = {
                'ficha': ficha,
                'dias_restantes': dias_restantes,
                'aprendices_activos': aprendices_activos,
                'instructor': ficha.instructor_lider,
            }
            
            html_content = render_to_string('alertas/email_ficha_proxima_vencer.html', context)
            text_content = render_to_string('alertas/email_ficha_proxima_vencer.txt', context)
            
            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [ficha.instructor_lider.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            emails_enviados += 1
            logger.info(f"Alerta enviada a {ficha.instructor_lider.email} para ficha {ficha.numero}")
            
        except Exception as e:
            logger.error(f"Error enviando alerta para ficha {ficha.numero}: {e}")
    
    return f"Alertas enviadas: {emails_enviados}"


@shared_task
def enviar_solicitud_subida_inasistencias():
    """
    Envía recordatorio a instructores para subir inasistencias del mes
    Se ejecuta el día 25 de cada mes
    """
    fichas_activas = Ficha.objects.filter(
        estado='ACTIVA',
        instructor_lider__isnull=False
    ).select_related('instructor_lider', 'programa')
    
    emails_enviados = 0
    mes_actual = timezone.now().strftime('%B %Y')
    
    for ficha in fichas_activas:
        try:
            # Verificar si ya subió inasistencias este mes
            inicio_mes = timezone.now().replace(day=1)
            
            tiene_inasistencias_mes = Inasistencia.objects.filter(
                aprendiz__ficha=ficha,
                fecha__gte=inicio_mes,
                importado_desde_excel=True
            ).exists()
            
            if tiene_inasistencias_mes:
                continue  # Ya subió este mes
            
            # Preparar email
            subject = f'📋 Recordatorio: Subir inasistencias de {mes_actual} - Ficha {ficha.numero}'
            
            context = {
                'ficha': ficha,
                'mes': mes_actual,
                'instructor': ficha.instructor_lider,
            }
            
            html_content = render_to_string('alertas/email_solicitud_inasistencias.html', context)
            text_content = render_to_string('alertas/email_solicitud_inasistencias.txt', context)
            
            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [ficha.instructor_lider.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            emails_enviados += 1
            logger.info(f"Solicitud inasistencias enviada a {ficha.instructor_lider.email} para ficha {ficha.numero}")
            
        except Exception as e:
            logger.error(f"Error enviando solicitud inasistencias para ficha {ficha.numero}: {e}")
    
    return f"Solicitudes enviadas: {emails_enviados}"


@shared_task
def enviar_solicitud_resultados_evaluativos():
    """
    Envía recordatorio a instructores para subir resultados evaluativos
    Se ejecuta cada 60 días
    """
    fichas_activas = Ficha.objects.filter(
        estado='ACTIVA',
        instructor_lider__isnull=False
    ).select_related('instructor_lider', 'programa')
    
    emails_enviados = 0
    
    for ficha in fichas_activas:
        try:
            # Verificar si tiene evaluaciones recientes (últimos 60 días)
            fecha_limite = timezone.now() - timedelta(days=60)
            
            tiene_evaluaciones_recientes = JuicioEvaluativo.objects.filter(
                aprendiz__ficha=ficha,
                fecha_registro__gte=fecha_limite,
                importado_desde_excel=True
            ).exists()
            
            if tiene_evaluaciones_recientes:
                continue  # Ya subió recientemente
            
            # Contar aprendices sin evaluaciones completas
            aprendices_sin_evaluar = ficha.aprendices.filter(
                activo=True,
                estado_formacion__in=['EN_FORMACION', 'CONDICIONADO']
            ).annotate(
                evaluaciones_pendientes=Count('juicios_evaluativos', filter=Q(juicios_evaluativos__juicio='PENDIENTE'))
            ).filter(evaluaciones_pendientes__gt=0).count()
            
            if aprendices_sin_evaluar == 0:
                continue
            
            # Preparar email
            subject = f'📊 Recordatorio: Subir resultados evaluativos - Ficha {ficha.numero}'
            
            context = {
                'ficha': ficha,
                'aprendices_sin_evaluar': aprendices_sin_evaluar,
                'instructor': ficha.instructor_lider,
            }
            
            html_content = render_to_string('alertas/email_solicitud_evaluaciones.html', context)
            text_content = render_to_string('alertas/email_solicitud_evaluaciones.txt', context)
            
            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [ficha.instructor_lider.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            emails_enviados += 1
            logger.info(f"Solicitud evaluaciones enviada a {ficha.instructor_lider.email} para ficha {ficha.numero}")
            
        except Exception as e:
            logger.error(f"Error enviando solicitud evaluaciones para ficha {ficha.numero}: {e}")
    
    return f"Solicitudes enviadas: {emails_enviados}"


@shared_task
def generar_informe_depuracion_bimensual():
    """
    Genera informe bimensual de depuración según Circular 120 Tabla 1 Caso 1
    """
    dias_limite = settings.CIRCULAR_120['DIAS_DEFINIR_MODALIDAD_PRODUCTIVA']
    fecha_limite = timezone.now().date() - timedelta(days=dias_limite)
    
    # Aprendices en riesgo
    aprendices_riesgo = Aprendiz.objects.filter(
        estado_formacion__in=['EN_FORMACION', 'CONDICIONADO', 'APLAZADO', 'REINGRESADO'],
        ficha__fecha_fin_lectiva__lt=fecha_limite,
        activo=True
    ).select_related('ficha', 'ficha__programa')
    
    # Aprendices certificados en el bimestre
    hace_60_dias = timezone.now() - timedelta(days=60)
    aprendices_certificados = Aprendiz.objects.filter(
        estado_formacion='CERTIFICADO',
        fecha_actualizacion__gte=hace_60_dias
    ).count()
    
    # Aprendices con deserción declarada
    aprendices_desercion = Aprendiz.objects.filter(
        estado_formacion='CANCELADO',
        fecha_actualizacion__gte=hace_60_dias
    ).count()
    
    # Preparar informe
    informe = {
        'fecha_generacion': timezone.now(),
        'periodo': f'{(timezone.now() - timedelta(days=60)).strftime("%d/%m/%Y")} - {timezone.now().strftime("%d/%m/%Y")}',
        'aprendices_riesgo': aprendices_riesgo.count(),
        'aprendices_certificados': aprendices_certificados,
        'aprendices_desercion': aprendices_desercion,
        'fichas_evaluadas': Ficha.objects.filter(
            aprendices__fecha_actualizacion__gte=hace_60_dias
        ).distinct().count(),
    }
    
    logger.info(f"Informe bimensual generado: {informe}")
    
    # TODO: Enviar informe a Coordinador Misional y Asesor GAE
    # según requerimientos de Circular 120
    
    return informe


@shared_task
def actualizar_estados_aprendices_circular120():
    """
    Actualiza automáticamente estados de aprendices según Circular 120
    """
    actualizados = 0
    
    # Actualizar a VIGENCIA_VENCIDA según Caso 1
    dias_limite = settings.CIRCULAR_120['DIAS_DEFINIR_MODALIDAD_PRODUCTIVA']
    fecha_limite = timezone.now().date() - timedelta(days=dias_limite)
    
    aprendices_vencidos = Aprendiz.objects.filter(
        estado_formacion__in=['EN_FORMACION', 'CONDICIONADO'],
        ficha__fecha_fin_lectiva__lt=fecha_limite,
        activo=True
    )
    
    for aprendiz in aprendices_vencidos:
        aprendiz.estado_formacion = 'VIGENCIA_VENCIDA'
        aprendiz.observaciones = f"Vigencia vencida automáticamente según Circular 120 - {timezone.now().strftime('%d/%m/%Y')}"
        aprendiz.save()
        actualizados += 1
        logger.info(f"Aprendiz {aprendiz.documento} actualizado a VIGENCIA_VENCIDA")
    
    return f"Aprendices actualizados: {actualizados}"


# apps/alertas/celery_schedule.py
# Configuración de tareas periódicas para celery beat
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'alerta-fichas-proximas-vencer': {
        'task': 'apps.alertas.tasks.enviar_alerta_fichas_proximas_vencer',
        'schedule': crontab(hour=8, minute=0, day_of_week='monday'),  # Lunes 8am
    },
    'solicitud-inasistencias-mensual': {
        'task': 'apps.alertas.tasks.enviar_solicitud_subida_inasistencias',
        'schedule': crontab(hour=9, minute=0, day_of_month='25'),  # Día 25 de cada mes
    },
    'solicitud-evaluaciones': {
        'task': 'apps.alertas.tasks.enviar_solicitud_resultados_evaluativos',
        'schedule': crontab(hour=9, minute=0, day_of_week='friday'),  # Viernes 9am
    },
    'informe-depuracion-bimensual': {
        'task': 'apps.alertas.tasks.generar_informe_depuracion_bimensual',
        'schedule': crontab(hour=7, minute=0, day_of_month='1'),  # Día 1 de cada mes
    },
    'actualizar-estados-circular120': {
        'task': 'apps.alertas.tasks.actualizar_estados_aprendices_circular120',
        'schedule': crontab(hour=2, minute=0),  # Diariamente a las 2am
    },
}