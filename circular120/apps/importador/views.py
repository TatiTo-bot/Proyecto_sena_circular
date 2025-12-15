import os
import time
import logging
from datetime import timedelta, date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .forms import ImportarInasistenciasForm, ImportarEvaluacionesForm
from .models import ArchivoImportado
from .excel_parser import ExcelParser

from apps.aprendices.models import Aprendiz
from apps.inasistencias.models import Inasistencia
from apps.evaluaciones.models import JuicioEvaluativo
from apps.competencias.models import ResultadoAprendizaje
from apps.fichas.models import Ficha

logger = logging.getLogger('importador')


# ---------- Helpers ----------
def daterange(start_date: date, end_date: date):
    """Generador de fechas inclusive"""
    current = start_date
    while current <= end_date:
        yield current
        current = current + timedelta(days=1)


# ===========================
# IMPORTAR INASISTENCIAS
# ===========================
@login_required
def importar_inasistencias(request):

    if request.method == 'POST':
        archivo_excel = request.FILES.get('archivo')
        
        if not archivo_excel:
            messages.error(request, '❌ No se seleccionó ningún archivo')
            return redirect('importador:importar_inasistencias')
        
        # Validar extensión
        nombre_archivo = archivo_excel.name.lower()
        if not (nombre_archivo.endswith('.xlsx') or nombre_archivo.endswith('.xls')):
            messages.error(request, '❌ El archivo debe ser de formato Excel (.xlsx o .xls)')
            return redirect('importador:importar_inasistencias')
        
        # Validar tamaño (10MB)
        if archivo_excel.size > 10 * 1024 * 1024:
            messages.error(request, '❌ El archivo es muy grande. Máximo 10MB permitido')
            return redirect('importador:importar_inasistencias')

        timestamp = int(time.time())
        filename = f"inasistencias_{timestamp}_{archivo_excel.name}"
        filepath = os.path.join(settings.EXCEL_UPLOAD_DIR, filename)

        # Guardar archivo
        try:
            with open(filepath, 'wb+') as destination:
                for chunk in archivo_excel.chunks():
                    destination.write(chunk)
        except Exception as e:
            messages.error(request, f'❌ Error al guardar el archivo: {str(e)}')
            return redirect('importador:importar_inasistencias')

        # Crear registro de importación
        archivo_importado = ArchivoImportado.objects.create(
            tipo='INASISTENCIAS',
            archivo=archivo_excel,
            usuario=request.user,
            estado='PROCESANDO'
        )

        try:
            inicio = time.time()
            parser = ExcelParser(filepath)

            if not parser.load_file():
                raise Exception("No se pudo leer el archivo Excel. Verifica que sea un archivo válido.")

            registros, errores = parser.parse_inasistencias()
            
            if not registros:
                error_msg = "No se encontraron registros válidos en el archivo."
                if errores:
                    error_msg += f" Errores encontrados: {', '.join(errores[:3])}"
                raise Exception(error_msg)

            importados = 0
            omitidos = 0
            errores_detallados = []
            aprendices_creados = 0
            fichas_creadas = 0

            with transaction.atomic():
                for registro in registros:
                    try:
                        # Buscar o crear ficha
                        if registro.get('numero_ficha'):
                            ficha, created = Ficha.objects.get_or_create(
                                numero=registro['numero_ficha'],
                                defaults={
                                    'estado': 'ACTIVA',
                                    'fecha_inicio': timezone.now().date(),
                                    'fecha_fin_lectiva': timezone.now().date() + timedelta(days=540),
                                }
                            )
                            if created:
                                fichas_creadas += 1
                                logger.info(f"Ficha {ficha.numero} creada automáticamente")
                        else:
                            # Ficha por defecto
                            ficha = Ficha.objects.first()
                            if not ficha:
                                # Crear ficha por defecto
                                from apps.fichas.models import Programa
                                programa, _ = Programa.objects.get_or_create(
                                    codigo='DEFAULT',
                                    defaults={
                                        'nombre': 'Programa General',
                                        'nivel': 'TECNOLOGO',
                                        'duracion_meses': 24,
                                    }
                                )
                                ficha = Ficha.objects.create(
                                    numero='DEFAULT-001',
                                    programa=programa,
                                    estado='ACTIVA',
                                    fecha_inicio=timezone.now().date(),
                                    fecha_fin_lectiva=timezone.now().date() + timedelta(days=540),
                                )
                                fichas_creadas += 1
                        
                        # Actualizar ficha del archivo
                        if not archivo_importado.ficha:
                            archivo_importado.ficha = ficha
                            archivo_importado.save()

                        # Buscar o crear aprendiz
                        aprendiz, created = Aprendiz.objects.get_or_create(
                            documento=registro['documento'],
                            defaults={
                                'tipo_documento': 'CC',
                                'nombre': registro.get('nombre', 'Aprendiz').split()[0] if registro.get('nombre') else 'Aprendiz',
                                'apellido': ' '.join(registro.get('nombre', 'Sin Apellido').split()[1:]) if registro.get('nombre') and len(registro.get('nombre', '').split()) > 1 else 'Sin Apellido',
                                'email': f"{registro['documento']}@misena.edu.co",
                                'ficha': ficha,
                                'estado_formacion': 'EN_FORMACION',
                                'activo': True,
                            }
                        )
                        
                        if created:
                            aprendices_creados += 1
                            logger.info(f"Aprendiz {aprendiz.documento} creado automáticamente")
                        
                        # Si ya existe pero no tiene ficha, asignarla
                        if not created and not aprendiz.ficha:
                            aprendiz.ficha = ficha
                            aprendiz.save()

                        # Crear o actualizar inasistencia
                        Inasistencia.objects.update_or_create(
                            aprendiz=aprendiz,
                            fecha=registro['fecha'],
                            defaults={
                                'justificada': registro.get('justificada', False),
                                'motivo': registro.get('observacion', ''),
                                'importado_desde_excel': True,
                                'archivo_origen': archivo_importado,
                            }
                        )

                        importados += 1

                    except Exception as e:
                        errores_detallados.append(
                            f"Fila {registro.get('fila_excel', '?')}: {str(e)}"
                        )
                        omitidos += 1
                        logger.error(f"Error procesando registro: {e}")

            fin = time.time()
            
            # Actualizar estado del archivo
            archivo_importado.estado = 'COMPLETADO'
            archivo_importado.registros_importados = importados
            archivo_importado.registros_omitidos = omitidos
            archivo_importado.registros_error = len(errores_detallados)
            archivo_importado.tiempo_proceso = fin - inicio
            archivo_importado.log_errores = '\n'.join(errores_detallados + errores)
            archivo_importado.save()

            # Mensajes de éxito
            messages.success(
                request, 
                f"✅ Importación completada: {importados} inasistencias registradas"
            )
            
            if aprendices_creados > 0:
                messages.info(request, f"📝 Se crearon {aprendices_creados} nuevos aprendices automáticamente")
            
            if fichas_creadas > 0:
                messages.info(request, f"📁 Se crearon {fichas_creadas} nuevas fichas")
            
            if omitidos > 0:
                messages.warning(request, f"⚠️ {omitidos} registros omitidos. Ver detalles en el historial.")

            return redirect('importador:detalle', pk=archivo_importado.id)

        except Exception as e:
            archivo_importado.estado = 'ERROR'
            archivo_importado.log_errores = str(e)
            archivo_importado.save()
            messages.error(request, f"❌ Error en la importación: {str(e)}")
            logger.error(f"Error en importación: {e}", exc_info=True)
            return redirect('importador:importar_inasistencias')

    return render(request, 'importador/importar_inasistencias.html')

    if request.method == 'POST':
        archivo_excel = request.FILES.get('archivo')
        
if not archivo_excel:
        messages.error(request, '❌ No se seleccionó ningún archivo')
        return redirect('importador:importar_inasistencias')

    timestamp = int(time.time())
    filename = f"inasistencias_{timestamp}_{archivo_excel.name}"
    filepath = os.path.join(settings.EXCEL_UPLOAD_DIR, filename)

        # Guardar archivo
    with open(filepath, 'wb+') as destination:
        for chunk in archivo_excel.chunks():
            destination.write(chunk)

        # Crear registro de importación
        archivo_importado = ArchivoImportado.objects.create(
            tipo='INASISTENCIAS',
            archivo=archivo_excel,
            usuario=request.user,
            estado='PROCESANDO'
        )

        try:
            inicio = time.time()
            parser = ExcelParser(filepath)

            if not parser.load_file():
                raise Exception("No se pudo leer el archivo Excel")

            registros, errores = parser.parse_inasistencias()
            
            if not registros:
                raise Exception("No se encontraron registros válidos en el archivo")

            importados = 0
            omitidos = 0
            errores_detallados = []
            aprendices_creados = 0
            fichas_creadas = 0

            with transaction.atomic():
                for registro in registros:
                    try:
                        # Buscar o crear ficha
                        if registro.get('numero_ficha'):
                            ficha, created = Ficha.objects.get_or_create(
                                numero=registro['numero_ficha'],
                                defaults={
                                    'estado': 'ACTIVA',
                                    'fecha_inicio': timezone.now().date(),
                                    'fecha_fin_lectiva': timezone.now().date() + timedelta(days=540),
                                }
                            )
                            if created:
                                fichas_creadas += 1
                                logger.info(f"Ficha {ficha.numero} creada automáticamente")
                        else:
                            # Ficha por defecto
                            ficha = Ficha.objects.first()
                            if not ficha:
                                errores_detallados.append(
                                    f"Fila {registro['fila_excel']}: No hay fichas disponibles"
                                )
                                omitidos += 1
                                continue
                        
                        # Actualizar ficha del archivo
                        if not archivo_importado.ficha:
                            archivo_importado.ficha = ficha
                            archivo_importado.save()

                        # Buscar o crear aprendiz
                        aprendiz, created = Aprendiz.objects.get_or_create(
                            documento=registro['documento'],
                            defaults={
                                'tipo_documento': 'CC',
                                'nombre': registro.get('nombre', 'Aprendiz'),
                                'apellido': '',
                                'email': f"{registro['documento']}@misena.edu.co",
                                'ficha': ficha,
                                'estado_formacion': 'EN_FORMACION',
                                'activo': True,
                            }
                        )
                        
                        if created:
                            aprendices_creados += 1
                            logger.info(f"Aprendiz {aprendiz.documento} creado automáticamente")
                        
                        # Si ya existe pero no tiene ficha, asignarla
                        if not created and not aprendiz.ficha:
                            aprendiz.ficha = ficha
                            aprendiz.save()

                        # Crear o actualizar inasistencia
                        Inasistencia.objects.update_or_create(
                            aprendiz=aprendiz,
                            fecha=registro['fecha'],
                            defaults={
                                'justificada': registro.get('justificada', False),
                                'motivo': registro.get('observacion', ''),
                                'importado_desde_excel': True,
                                'archivo_origen': archivo_importado,
                            }
                        )

                        importados += 1

                    except Exception as e:
                        errores_detallados.append(
                            f"Fila {registro.get('fila_excel', '?')}: {str(e)}"
                        )
                        omitidos += 1
                        logger.error(f"Error procesando registro: {e}")

            fin = time.time()
            
            # Actualizar estado del archivo
            archivo_importado.estado = 'COMPLETADO'
            archivo_importado.registros_importados = importados
            archivo_importado.registros_omitidos = omitidos
            archivo_importado.registros_error = len(errores_detallados)
            archivo_importado.tiempo_proceso = fin - inicio
            archivo_importado.log_errores = '\n'.join(errores_detallados + errores)
            archivo_importado.save()

            # Mensajes de éxito
            messages.success(
                request, 
                f"✅ Importación completada: {importados} registros importados"
            )
            
            if aprendices_creados > 0:
                messages.info(request, f"📝 Se crearon {aprendices_creados} nuevos aprendices")
            
            if fichas_creadas > 0:
                messages.info(request, f"📁 Se crearon {fichas_creadas} nuevas fichas")
            
            if omitidos > 0:
                messages.warning(request, f"⚠️ {omitidos} registros omitidos (ver detalles)")

            return redirect('importador:detalle', pk=archivo_importado.id)

        except Exception as e:
            archivo_importado.estado = 'ERROR'
            archivo_importado.log_errores = str(e)
            archivo_importado.save()
            messages.error(request, f"❌ Error en la importación: {str(e)}")
            logger.error(f"Error en importación: {e}", exc_info=True)
            return redirect('importador:importar_inasistencias')

    return render(request, 'importador/importar_inasistencias.html')

# ===========================
# IMPORTAR EVALUACIONES
# ===========================
@login_required
def importar_evaluaciones(request):
    if request.method == 'POST':
        form = ImportarEvaluacionesForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Formulario inválido. Verifica el archivo.")
            return redirect('importador:importar_evaluaciones')

        archivo_excel = request.FILES.get('archivo')
        if not archivo_excel:
            messages.error(request, '❌ No se seleccionó ningún archivo')
            return redirect('importador:importar_evaluaciones')

        timestamp = int(time.time())
        filename = f"evaluaciones_{timestamp}_{archivo_excel.name}"
        os.makedirs(settings.EXCEL_UPLOAD_DIR, exist_ok=True)
        filepath = os.path.join(settings.EXCEL_UPLOAD_DIR, filename)

        with open(filepath, 'wb+') as destination:
            for chunk in archivo_excel.chunks():
                destination.write(chunk)

        try:
            inicio = time.time()
            parser = ExcelParser(filepath)

            if not parser.load_file():
                raise Exception("No se pudo cargar el archivo")

            # Intentar obtener numero de ficha desde el excel (método del parser)
            numero_ficha = None
            try:
                numero_ficha = parser.ficha_numero or parser.get_ficha_from_excel() if hasattr(parser, 'get_ficha_from_excel') else None
            except Exception:
                numero_ficha = None

            if not numero_ficha:
                # fallback: pedir al usuario (o crear ficha por defecto)
                numero_ficha = form.cleaned_data.get('numero_ficha') or None

            ficha, creada_ficha = Ficha.objects.get_or_create(numero=numero_ficha or '0000')

            archivo_importado = ArchivoImportado.objects.create(
                tipo='EVALUACIONES',
                archivo=archivo_excel,
                usuario=request.user,
                ficha=ficha,
                estado='PROCESANDO'
            )

            columnas_detectadas = {}
            if hasattr(parser, 'detect_columns_evaluaciones'):
                columnas_detectadas = parser.detect_columns_evaluaciones()
            else:
                # Si el parser no implementa ese método, asumimos que parse_evaluaciones devolverá error si faltan columnas.
                columnas_detectadas = {}

            registros, errores_parser = parser.parse_evaluaciones() if hasattr(parser, 'parse_evaluaciones') else ([], ["Parser no implementa parse_evaluaciones"])

            if errores_parser and not registros:
                raise Exception(" | ".join(errores_parser))

            importados = 0
            omitidos = 0
            errores_detallados = []

            with transaction.atomic():
                for registro in registros:
                    try:
                        documento = str(registro.get('documento') or '').strip()
                        if not documento:
                            omitidos += 1
                            errores_detallados.append(f"Fila {registro.get('fila_excel','?')}: Documento vacío")
                            continue

                        # Buscar aprendiz por documento y ficha
                        aprendiz = Aprendiz.objects.filter(documento=documento, ficha=ficha).first()
                        if not aprendiz:
                            omitidos += 1
                            errores_detallados.append(f"Fila {registro.get('fila_excel','?')}: Aprendiz no encontrado en ficha {ficha.numero}")
                            continue

                        ra_codigo = registro.get('ra_codigo') or registro.get('resultado_aprendizaje') or registro.get('ra') or registro.get('codigo_ra')
                        ra = ResultadoAprendizaje.objects.filter(codigo=ra_codigo).first()
                        if not ra:
                            omitidos += 1
                            errores_detallados.append(f"Fila {registro.get('fila_excel','?')}: Resultado de aprendizaje no encontrado ({ra_codigo})")
                            continue

                        JuicioEvaluativo.objects.update_or_create(
                            aprendiz=aprendiz,
                            resultado_aprendizaje=ra,
                            fecha_evaluacion=registro.get('fecha_evaluacion') or timezone.now().date(),
                            defaults={
                                'juicio': registro.get('juicio'),
                                'importado_desde_excel': True,
                                'archivo_origen': archivo_importado,
                            }
                        )
                        importados += 1

                    except Exception as e:
                        logger.exception("Error procesando evaluación")
                        errores_detallados.append(f"Fila {registro.get('fila_excel','?')}: {str(e)}")
                        omitidos += 1

            fin = time.time()

            archivo_importado.estado = 'COMPLETADO'
            archivo_importado.registros_importados = importados
            archivo_importado.registros_omitidos = omitidos
            archivo_importado.registros_error = len(errores_detallados) + len(errores_parser)
            archivo_importado.tiempo_proceso = fin - inicio
            archivo_importado.log_errores = '\n'.join(errores_detallados + errores_parser)
            archivo_importado.save()

            messages.success(request, f'✅ Evaluaciones importadas correctamente | Ficha {ficha.numero}')
            return redirect('importador:historial')

        except Exception as e:
            logger.exception("Error importando evaluaciones")
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('importador:importar_evaluaciones')

    else:
        form = ImportarEvaluacionesForm()

    return render(request, 'importador/importar_evaluaciones.html', {'form': form})


# ===========================
# HISTORIAL Y DETALLE
# ===========================
@login_required
def historial_importaciones(request):
    archivos = ArchivoImportado.objects.filter(
        usuario=request.user
    ).select_related('ficha', 'usuario').order_by('-fecha_importacion')[:50]

    return render(request, 'importador/historial.html', {'archivos': archivos})


@login_required
def detalle_importacion(request, pk):
    archivo = get_object_or_404(ArchivoImportado, pk=pk)

    if archivo.usuario != request.user and not request.user.is_staff:
        messages.error(request, "No tienes permiso para ver este archivo.")
        return redirect('importador:historial')

    return render(request, 'importador/detalle.html', {'archivo': archivo})


# Plantilla para descarga (simple)
@login_required
def descargar_plantilla(request, tipo):
    # Puedes devolver archivos reales; por ahora devuelvo texto simple
    contenido = f"Plantilla para {tipo}. Coloca columnas: Documento, Ficha, Fecha Inicio, Fecha Fin, Observacion"
    response = HttpResponse(contenido, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename=plantilla_{tipo}.txt'
    return response
