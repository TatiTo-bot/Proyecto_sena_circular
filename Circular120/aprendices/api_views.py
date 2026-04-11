# aprendices/api_views.py - CREAR ESTE ARCHIVO

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.serializers import serialize
from .models import Aprendiz, Ficha, CentroFormacion, RolAdministrativo
import json

@login_required
@require_http_methods(["GET"])
def aprendices_json(request):
    """API JSON para lista de aprendices con filtros"""
    
    ficha_id = request.GET.get('ficha')
    estado = request.GET.get('estado')
    
    aprendices = Aprendiz.objects.select_related('ficha').all()
    
    if ficha_id:
        aprendices = aprendices.filter(ficha__numero=ficha_id)
    
    if estado:
        aprendices = aprendices.filter(estado_formacion=estado)
    
    data = {
        'success': True,
        'count': aprendices.count(),
        'aprendices': [
            {
                'documento': a.documento,
                'nombre_completo': f"{a.nombre} {a.apellido}",
                'ficha': a.ficha.numero if a.ficha else None,
                'programa': a.ficha.programa if a.ficha else None,
                'estado': a.get_estado_formacion_display(),
                'fecha_inicio': a.fecha_inicio.isoformat() if a.fecha_inicio else None,
                'fecha_final': a.fecha_final.isoformat() if a.fecha_final else None,
            }
            for a in aprendices[:100]  # Limitar a 100 resultados
        ]
    }
    
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def fichas_json(request):
    """API JSON para lista de fichas"""
    
    centro_id = request.GET.get('centro')
    
    fichas = Ficha.objects.all()
    
    if centro_id:
        fichas = fichas.filter(centro__codigo=centro_id)
    
    data = {
        'success': True,
        'count': fichas.count(),
        'fichas': [
            {
                'numero': f.numero,
                'programa': f.programa,
                'instructor': f.instructor,
                'fecha_inicio': f.fecha_inicio.isoformat() if f.fecha_inicio else None,
                'fecha_fin': f.fecha_fin.isoformat() if f.fecha_fin else None,
                'total_aprendices': f.aprendices.count(),
            }
            for f in fichas
        ]
    }
    
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def centros_json(request):
    """API JSON para lista de centros de formación"""
    
    activos = request.GET.get('activos', 'true') == 'true'
    
    centros = CentroFormacion.objects.all()
    
    if activos:
        centros = centros.filter(activo=True)
    
    data = {
        'success': True,
        'count': centros.count(),
        'centros': [
            {
                'codigo': c.codigo,
                'nombre': c.nombre,
                'municipio': c.municipio,
                'direccion': c.direccion,
                'telefono': c.telefono,
                'email': c.email,
                'activo': c.activo,
            }
            for c in centros
        ]
    }
    
    return JsonResponse(data)


@login_required
@require_http_methods(["GET"])
def roles_json(request):
    """API JSON para roles administrativos"""
    
    centro_id = request.GET.get('centro')
    tipo_rol = request.GET.get('tipo')
    activos = request.GET.get('activos', 'true') == 'true'
    
    roles = RolAdministrativo.objects.select_related('usuario', 'centro').all()
    
    if centro_id:
        roles = roles.filter(centro__codigo=centro_id)
    
    if tipo_rol:
        roles = roles.filter(tipo_rol=tipo_rol)
    
    if activos:
        roles = roles.filter(activo=True)
    
    data = {
        'success': True,
        'count': roles.count(),
        'roles': [
            {
                'id': r.id,
                'usuario': {
                    'username': r.usuario.username,
                    'nombre_completo': r.usuario.get_full_name(),
                    'email': r.usuario.email,
                },
                'tipo_rol': r.get_tipo_rol_display(),
                'centro': {
                    'codigo': r.centro.codigo,
                    'nombre': r.centro.nombre,
                },
                'fecha_inicio': r.fecha_inicio.isoformat(),
                'fecha_fin': r.fecha_fin.isoformat() if r.fecha_fin else None,
                'activo': r.activo,
            }
            for r in roles
        ]
    }
    
    return JsonResponse(data)


@login_required
@require_http_methods(["POST"])
def deshabilitar_rol(request, rol_id):
    """Deshabilitar un rol administrativo"""
    
    try:
        rol = RolAdministrativo.objects.get(id=rol_id)
        rol.deshabilitar()
        
        return JsonResponse({
            'success': True,
            'message': f'Rol {rol.get_tipo_rol_display()} deshabilitado correctamente'
        })
    except RolAdministrativo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Rol no encontrado'
        }, status=404)