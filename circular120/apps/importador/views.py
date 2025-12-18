import os
import time
import logging
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import ArchivoImportado
from .excel_parser import ExcelParser

from apps.aprendices.models import Aprendiz
from apps.inasistencias.models import Inasistencia
from apps.evaluaciones.models import JuicioEvaluativo
from apps.competencias.models import ResultadoAprendizaje, Competencia
from apps.fichas.models import Ficha, Programa

logger = logging.getLogger('importador')


def crear_o_obtener_programa_default():
    """Crea o obtiene el programa por defecto"""
    programa, created = Programa.objects.get_or_create(
        codigo='GENERAL-001',
        defaults={
            'nombre': 'Programa General SENA',
            'nivel': 'TECNOLOGO',
            'duracion_meses': 24,
            'activo': True,
        }
    )
    return programa


def crear_o_obtener_programa(nombre_programa=None, codigo_programa=None):
    """Crea o obtiene un programa"""
    if nombre_programa:
        # Limpiar nombre
        nombre_programa = nombre_programa.strip().upper()
        
        # Buscar por nombre similar
        programa = Programa.objects.filter(nombre__icontains=nombre_programa[:30]).first()
        if programa:
            return programa
        
        # Crear nuevo programa
        codigo = codigo_programa or f'PROG-{int(time.time())}'
        programa = Programa.objects.create(
            codigo=codigo,
            nombre=nombre_programa,
            nivel='TECNOLOGO',
            duracion_meses=24,
            activo=True,
        )
        logger.info(f"Programa '{nombre_programa}' creado automáticamente")
        return programa
    
    return crear_o_obtener_programa_default()


def crear_o_obtener_ficha(numero_ficha, programa_nombre=None):
    """Crea o obtiene una ficha por su número"""
    if not numero_ficha:
        numero_ficha = f'DEFAULT-{int(time.time())}'
    
    # Buscar ficha existente
    ficha = Ficha.objects.filter(numero=numero_ficha).first()
    if ficha:
        return ficha
    
    # Crear nueva ficha
    programa = crear_o_obtener_programa(programa_nombre, numero_ficha)
    
    ficha = Ficha.objects.create(
        numero=numero_ficha,
        programa=programa,
        estado='ACTIVA',
        fecha_inicio=timezone.now().date(),
        fecha_fin_lectiva=timezone.now().date() + timedelta(days=540),
        fecha_fin_practica=timezone.now().date() + timedelta(days=720),
    )
    
    logger.info(f"Ficha {numero_ficha} creada automáticamente con programa {programa.nombre}")
    return ficha


def crear_o_obtener_aprendiz(tipo_doc, documento, nombre, apellido, ficha):
    """Crea o obtiene un aprendiz"""
    # Buscar por documento
    aprendiz = Aprendiz.objects.filter(documento=documento).first()
    
    if aprendiz:
        # Actualizar si no tiene datos
        actualizado = False
        if not aprendiz.ficha:
            aprendiz.ficha = ficha
            actualizado = True
        if not aprendiz.nombre and nombre:
            aprendiz.nombre = nombre
            actualizado = True
        if not aprendiz.apellido and apellido:
            aprendiz.apellido = apellido
            actualizado = True
        if not aprendiz.tipo_documento or aprendiz.tipo_documento == 'CC':
            aprendiz.tipo_documento = tipo_doc
            actualizado = True
        
        if actualizado:
            aprendiz.save()
            logger.info(f"Aprendiz {documento} actualizado")
        
        return aprendiz, False
    
    # Crear nuevo aprendiz
    aprendiz = Aprendiz.objects.create(
        documento=documento,
        tipo_documento=tipo_doc,
        nombre=nombre or 'Aprendiz',
        apellido=apellido or 'SENA',
        email=f"{documento}@misena.edu.co",
        ficha=ficha,
        estado_formacion='EN_FORMACION',
        activo=True,
    )
    
    logger.info(f"Aprendiz {tipo_doc} {documento} - {nombre} {apellido} creado automáticamente")
    return aprendiz, True


@login_required
def importar_inasistencias(request):
    """Vista para importar inasistencias desde Excel"""
    
    if request.method == 'POST':
        archivo_excel = request.FILES.get('archivo')
        
        if not archivo_excel:
            messages.error(request, '❌ No se seleccionó ningún archivo')
            return redirect('importador:importar_inasistencias')
        
        # Validar extensión
        nombre_archivo = archivo_excel.name.lower()
        if not (nombre_archivo.endswith('.xlsx') or nombre_archivo.endswith('.xls') or nombre_archivo.endswith('.xlsm')):
            messages.error(request, '❌ El archivo debe ser Excel (.xlsx, .xls o .xlsm)')
            return redirect('importador:importar_inasistencias')
        
        # Validar tamaño
        if archivo_excel.size > 10 * 1024 * 1024:
            messages.error(request, '❌ El archivo es muy grande. Máximo 10MB')
            return redirect('importador:importar_inasistencias')

        # Guardar archivo temporalmente
        timestamp = int(time.time())
        filename = f"inasistencias_{timestamp}_{archivo_excel.name}"
        os.makedirs(settings.EXCEL_UPLOAD_DIR, exist_ok=True)
        filepath = os.path.join(settings.EXCEL_UPLOAD_DIR, filename)

        try:
            with open(filepath, 'wb+') as destination:
                for chunk in archivo_excel.chunks():
                    destination.write(chunk)
        except Exception as e:
            messages.error(request, f'❌ Error al guardar archivo: {str(e)}')
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
                raise Exception("No se pudo leer el archivo Excel. Verifica que sea válido.")

            registros, errores_parser = parser.parse_inasistencias()
            
            if not registros:
                error_msg = "No se encontraron registros válidos."
                if errores_parser:
                    error_msg += f" Errores: {'; '.join(errores_parser[:3])}"
                raise Exception(error_msg)

            importados = 0
            omitidos = 0
            errores_detallados = []
            aprendices_creados = 0
            fichas_creadas = 0
            fichas_set = set()

            with transaction.atomic():
                for registro in registros:
                    try:
                        # Obtener o crear ficha
                        numero_ficha = registro.get('numero_ficha')
                        programa_nombre = registro.get('programa_nombre')
                        
                        ficha = crear_o_obtener_ficha(numero_ficha, programa_nombre)
                        
                        if numero_ficha and numero_ficha not in fichas_set:
                            fichas_set.add(numero_ficha)
                            fichas_creadas += 1
                        
                        # Asignar ficha al archivo si no tiene
                        if not archivo_importado.ficha:
                            archivo_importado.ficha = ficha
                            archivo_importado.save()

                        # Obtener o crear aprendiz
                        aprendiz, created = crear_o_obtener_aprendiz(
                            tipo_doc=registro.get('tipo_documento', 'CC'),
                            documento=registro['documento'],
                            nombre=registro.get('nombre', ''),
                            apellido=registro.get('apellido', ''),
                            ficha=ficha
                        )
                        
                        if created:
                            aprendices_creados += 1

                        # Crear o actualizar inasistencia
                        Inasistencia.objects.update_or_create(
                            aprendiz=aprendiz,
                            fecha=registro['fecha'],
                            defaults={
                                'justificada': registro.get('justificada', False),
                                'motivo': registro.get('observacion', ''),
                                'cant_horas': registro.get('cant_horas'),
                                'instructor': registro.get('instructor', ''),
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
            
            # Actualizar estado
            archivo_importado.estado = 'COMPLETADO'
            archivo_importado.registros_importados = importados
            archivo_importado.registros_omitidos = omitidos
            archivo_importado.registros_error = len(errores_detallados)
            archivo_importado.tiempo_proceso = fin - inicio
            archivo_importado.log_errores = '\n'.join(errores_detallados + errores_parser)
            archivo_importado.save()

            # Mensajes
            messages.success(request, f"✅ {importados} inasistencias importadas correctamente")
            
            if aprendices_creados > 0:
                messages.info(request, f"📝 {aprendices_creados} aprendices creados automáticamente")
            
            if fichas_creadas > 0:
                messages.info(request, f"📁 {fichas_creadas} fichas creadas automáticamente")
            
            if omitidos > 0:
                messages.warning(request, f"⚠️ {omitidos} registros omitidos (ver detalles)")

            return redirect('importador:detalle', pk=archivo_importado.id)

        except Exception as e:
            archivo_importado.estado = 'ERROR'
            archivo_importado.log_errores = str(e)
            archivo_importado.save()
            messages.error(request, f"❌ Error: {str(e)}")
            logger.error(f"Error en importación: {e}", exc_info=True)
            return redirect('importador:importar_inasistencias')
        finally:
            # Limpiar archivo temporal
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass

    return render(request, 'importador/importar_inasistencias.html')


@login_required
def importar_evaluaciones(request):
    """Vista para importar evaluaciones"""
    
    if request.method == 'POST':
        archivo_excel = request.FILES.get('archivo')
        
        if not archivo_excel:
            messages.error(request, '❌ No se seleccionó ningún archivo')
            return redirect('importador:importar_evaluaciones')
        
        # Validaciones
        nombre_archivo = archivo_excel.name.lower()
        if not (nombre_archivo.endswith('.xlsx') or nombre_archivo.endswith('.xls') or nombre_archivo.endswith('.xlsm')):
            messages.error(request, '❌ El archivo debe ser Excel')
            return redirect('importador:importar_evaluaciones')
        
        if archivo_excel.size > 10 * 1024 * 1024:
            messages.error(request, '❌ Archivo muy grande (máx 10MB)')
            return redirect('importador:importar_evaluaciones')

        # Guardar archivo
        timestamp = int(time.time())
        filename = f"evaluaciones_{timestamp}_{archivo_excel.name}"
        os.makedirs(settings.EXCEL_UPLOAD_DIR, exist_ok=True)
        filepath = os.path.join(settings.EXCEL_UPLOAD_DIR, filename)

        try:
            with open(filepath, 'wb+') as destination:
                for chunk in archivo_excel.chunks():
                    destination.write(chunk)
        except Exception as e:
            messages.error(request, f'❌ Error al guardar: {str(e)}')
            return redirect('importador:importar_evaluaciones')

        try:
            inicio = time.time()
            parser = ExcelParser(filepath)

            if not parser.load_file():
                raise Exception("No se pudo leer el archivo")

            registros, errores_parser = parser.parse_evaluaciones()
            
            if not registros:
                error_msg = "No se encontraron registros válidos."
                if errores_parser:
                    error_msg += f" Errores: {'; '.join(errores_parser[:3])}"
                raise Exception(error_msg)

            # Determinar ficha
            numero_ficha = registros[0].get('numero_ficha') if registros else None
            programa_nombre = registros[0].get('programa_nombre') if registros else None
            ficha = crear_o_obtener_ficha(numero_ficha, programa_nombre)

            archivo_importado = ArchivoImportado.objects.create(
                tipo='EVALUACIONES',
                archivo=archivo_excel,
                usuario=request.user,
                ficha=ficha,
                estado='PROCESANDO'
            )

            importados = 0
            omitidos = 0
            errores_detallados = []
            aprendices_creados = 0
            ras_creados = 0

            with transaction.atomic():
                for registro in registros:
                    try:
                        documento = registro.get('documento', '').strip()
                        if not documento:
                            omitidos += 1
                            continue

                        # Obtener o crear aprendiz
                        aprendiz, created = crear_o_obtener_aprendiz(
                            tipo_doc=registro.get('tipo_documento', 'CC'),
                            documento=documento,
                            nombre=registro.get('nombre', ''),
                            apellido=registro.get('apellido', ''),
                            ficha=ficha
                        )
                        
                        if created:
                            aprendices_creados += 1

                        # Buscar o crear RA
                        ra_codigo = registro.get('ra_codigo', '').strip()
                        if not ra_codigo:
                            errores_detallados.append(
                                f"Fila {registro.get('fila_excel','?')}: Código RA vacío"
                            )
                            omitidos += 1
                            continue
                        
                        ra = ResultadoAprendizaje.objects.filter(codigo=ra_codigo).first()
                        
                        if not ra:
                            # Crear RA genérico
                            competencia_default, _ = Competencia.objects.get_or_create(
                                codigo='COMP-GENERAL',
                                defaults={
                                    'nombre': 'Competencia General',
                                    'programa': ficha.programa,
                                    'duracion_horas': 100,
                                }
                            )
                            
                            ra = ResultadoAprendizaje.objects.create(
                                codigo=ra_codigo,
                                descripcion=f'Resultado de Aprendizaje {ra_codigo}',
                                competencia=competencia_default
                            )
                            ras_creados += 1
                            logger.info(f"RA {ra_codigo} creado automáticamente")

                        # Crear evaluación
                        fecha_eval = registro.get('fecha_evaluacion') or timezone.now().date()
                        
                        JuicioEvaluativo.objects.update_or_create(
                            aprendiz=aprendiz,
                            resultado_aprendizaje=ra,
                            fecha_evaluacion=fecha_eval,
                            defaults={
                                'juicio': registro.get('juicio', 'PENDIENTE'),
                                'importado_desde_excel': True,
                                'archivo_origen': archivo_importado,
                            }
                        )
                        
                        importados += 1

                    except Exception as e:
                        logger.exception(f"Error procesando evaluación")
                        errores_detallados.append(
                            f"Fila {registro.get('fila_excel','?')}: {str(e)}"
                        )
                        omitidos += 1

            fin = time.time()

            archivo_importado.estado = 'COMPLETADO'
            archivo_importado.registros_importados = importados
            archivo_importado.registros_omitidos = omitidos
            archivo_importado.registros_error = len(errores_detallados)
            archivo_importado.tiempo_proceso = fin - inicio
            archivo_importado.log_errores = '\n'.join(errores_detallados + errores_parser)
            archivo_importado.save()

            messages.success(request, f'✅ {importados} evaluaciones importadas | Ficha {ficha.numero}')
            
            if aprendices_creados > 0:
                messages.info(request, f"📝 {aprendices_creados} aprendices creados")
            
            if ras_creados > 0:
                messages.info(request, f"📋 {ras_creados} resultados de aprendizaje creados")
            
            if omitidos > 0:
                messages.warning(request, f"⚠️ {omitidos} registros omitidos")

            return redirect('importador:detalle', pk=archivo_importado.id)

        except Exception as e:
            logger.exception("Error importando evaluaciones")
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('importador:importar_evaluaciones')
        finally:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass

    # Obtener competencias disponibles
    competencias = Competencia.objects.all()[:50]
    
    return render(request, 'importador/importar_evaluaciones.html', {
        'competencias': competencias
    })


@login_required
def historial_importaciones(request):
    """Historial de importaciones"""
    archivos = ArchivoImportado.objects.filter(
        usuario=request.user
    ).select_related('ficha', 'usuario').order_by('-fecha_importacion')[:100]

    return render(request, 'importador/historial.html', {'archivos': archivos})


@login_required
def detalle_importacion(request, pk):
    """Detalle de una importación"""
    archivo = get_object_or_404(ArchivoImportado, pk=pk)

    if archivo.usuario != request.user and not request.user.is_staff:
        messages.error(request, "No tienes permiso para ver este archivo")
        return redirect('importador:historial')

    return render(request, 'importador/detalle.html', {'archivo': archivo})


@login_required
def validar_excel(request):
    """Vista para validar un archivo Excel antes de importar"""
    
    if request.method == 'POST':
        archivo_excel = request.FILES.get('archivo')
        
        if not archivo_excel:
            messages.error(request, 'No se seleccionó archivo')
            return redirect('importador:validar_excel')
        
        try:
            parser = ExcelParser(archivo_excel)
            
            if not parser.load_file():
                messages.error(request, 'No se pudo leer el archivo')
                return render(request, 'importador/validar_excel.html')
            
            # Parsear
            registros, errores = parser.parse_inasistencias()
            
            # Analizar columnas
            columnas_info = []
            mapeo_columnas = {
                'FICHA': 'ficha',
                'INSTRUCTOR': 'instructor',
                'IDENTIFICACION': 'documento',
                'APRENDIZ': 'nombre',
                'FECHA': 'fecha',
                'HORAS': 'horas',
                'JUSTIFICACION': 'justificación'
            }
            
            for col_original in parser.df.columns:
                col_norm = parser._normalize_column_name(col_original)
                
                tipo_detectado = None
                for clave, valor in mapeo_columnas.items():
                    if clave in col_norm:
                        tipo_detectado = valor
                        break
                
                columnas_info.append({
                    'original': col_original,
                    'normalizada': col_norm,
                    'tipo': tipo_detectado,
                    'ok': tipo_detectado is not None
                })
            
            # Extraer fichas y programas únicos
            fichas_unicas = set()
            programas_unicos = set()
            
            for reg in registros:
                if reg.get('numero_ficha'):
                    fichas_unicas.add(reg['numero_ficha'])
                if reg.get('programa_nombre'):
                    programas_unicos.add(reg['programa_nombre'])
            
            resultados = {
                'columnas': columnas_info,
                'registros': registros,
                'errores': errores,
                'total_filas': len(parser.df),
                'fichas_unicas': fichas_unicas,
                'programas_unicos': programas_unicos,
            }
            
            return render(request, 'importador/validar_excel.html', {
                'resultados': resultados
            })
            
        except Exception as e:
            logger.exception("Error validando Excel")
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'importador/validar_excel.html')


@login_required
def descargar_plantilla(request, tipo):
    """Descarga plantilla de ejemplo"""
    if tipo == 'inasistencias':
        contenido = """FICHA,INSTRUCTOR,IDENTIFICACIÓN APRENDIZ,APRENDIZ,FECHA INICIO,FECHA FIN,CANT. HORAS,JUSTIFICACION
2819058 - ANALISIS Y DESARROLLO DE SOFTWARE,Juan Instructor,CC - 1234567890,CARLOS PEREZ GOMEZ,01/12/2024,01/12/2024,6,NO PRESENTO SOPORTES
2819058 - ANALISIS Y DESARROLLO DE SOFTWARE,Juan Instructor,PPT - 0987654321,MARIA GONZALEZ LOPEZ,02/12/2024,02/12/2024,4,INCAPACIDAD MEDICA"""
    else:
        contenido = """FICHA,IDENTIFICACIÓN APRENDIZ,APRENDIZ,CODIGO RA,JUICIO,FECHA EVALUACION
2819058 - ANALISIS Y DESARROLLO DE SOFTWARE,CC - 1234567890,CARLOS PEREZ,22050104601,APROBADO,15/12/2024
2819058 - ANALISIS Y DESARROLLO DE SOFTWARE,PPT - 0987654321,MARIA GONZALEZ,22050104601,NO APROBADO,15/12/2024"""
    
    response = HttpResponse(contenido, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename=plantilla_{tipo}.csv'
    return response