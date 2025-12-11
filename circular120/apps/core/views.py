from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.aprendices.models import Aprendiz
from apps.fichas.models import Ficha
from apps.importador.models import ArchivoImportado


@login_required
def home(request):
    """
    Vista principal del sistema con estadísticas generales
    """
    
    # Estadísticas generales
    total_aprendices = Aprendiz.objects.filter(activo=True).count()
    total_fichas = Ficha.objects.filter(estado='ACTIVA').count()
    
    # Alertas activas (aprendices en riesgo)
    alertas_activas = Aprendiz.objects.filter(
        activo=True,
        estado_formacion__in=['VIGENCIA_VENCIDA', 'CONDICIONADO']
    ).count()
    
    # Tasa de certificación (últimos 6 meses)
    hace_6_meses = timezone.now() - timedelta(days=180)
    aprendices_certificados = Aprendiz.objects.filter(
        estado_formacion='CERTIFICADO',
        fecha_actualizacion__gte=hace_6_meses
    ).count()
    
    aprendices_totales_periodo = Aprendiz.objects.filter(
        fecha_registro__gte=hace_6_meses
    ).count()
    
    tasa_certificacion = 0
    if aprendices_totales_periodo > 0:
        tasa_certificacion = (aprendices_certificados / aprendices_totales_periodo) * 100
    
    # Actividad reciente (últimas importaciones)
    actividad_reciente = []
    
    archivos_recientes = ArchivoImportado.objects.select_related(
        'usuario', 'ficha'
    ).order_by('-fecha_importacion')[:5]
    
    for archivo in archivos_recientes:
        icono = 'file-earmark-excel'
        color = 'success'
        
        if archivo.estado == 'ERROR':
            color = 'danger'
            icono = 'x-circle'
        elif archivo.estado == 'PROCESANDO':
            color = 'warning'
            icono = 'hourglass-split'
        
        actividad_reciente.append({
            'titulo': f"Importación de {archivo.get_tipo_display()}",
            'descripcion': f"{archivo.usuario.get_full_name()} importó {archivo.registros_importados} registros",
            'fecha': archivo.fecha_importacion,
            'icono': icono,
            'color': color,
        })
    
    # Información del usuario actual
    perfil_usuario = getattr(request.user, 'perfil', None)
    
    # Si es instructor, mostrar sus fichas
    fichas_usuario = []
    if perfil_usuario and perfil_usuario.es_instructor():
        fichas_usuario = Ficha.objects.filter(
            instructor_lider=request.user,
            estado='ACTIVA'
        ).select_related('programa')[:5]
    
    context = {
        'total_aprendices': total_aprendices,
        'total_fichas': total_fichas,
        'alertas_activas': alertas_activas,
        'tasa_certificacion': tasa_certificacion,
        'actividad_reciente': actividad_reciente,
        'perfil_usuario': perfil_usuario,
        'fichas_usuario': fichas_usuario,
    }
    
    return render(request, 'home.html', context)