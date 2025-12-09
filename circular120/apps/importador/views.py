from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import time
import os

from .forms import ImportarInasistenciasForm, ImportarEvaluacionesForm
from .models import ArchivoImportado
from .excel_parser import ExcelParser

from apps.aprendices.models import Aprendiz
from apps.inasistencias.models import Inasistencia
from apps.evaluaciones.models import JuicioEvaluativo
from apps.competencias.models import ResultadoAprendizaje
from apps.fichas.models import Ficha

import logging
logger = logging.getLogger('importador')


# ✅ =========================
# ✅ IMPORTAR INASISTENCIAS
# ✅ =========================
@login_required
def importar_inasistencias(request):

    if request.method == 'POST':
        archivo_excel = request.FILES['archivo']

        timestamp = int(time.time())
        filename = f"inasistencias_{timestamp}_{archivo_excel.name}"
        filepath = os.path.join(settings.EXCEL_UPLOAD_DIR, filename)

        with open(filepath, 'wb+') as destination:
            for chunk in archivo_excel.chunks():
                destination.write(chunk)

        archivo_importado = ArchivoImportado.objects.create(
            tipo='INASISTENCIAS',
            archivo=archivo_excel,
            usuario=request.user,
            estado='PROCESANDO'
        )

        try:
            parser = ExcelParser(filepath)

            if not parser.load_file():
                raise Exception("No se pudo leer el archivo")

            registros, errores = parser.parse_inasistencias()

            importados = 0
            omitidos = 0
            errores_detallados = []

            with transaction.atomic():
                for registro in registros:

                    ficha, _ = Ficha.objects.get_or_create(
                        numero=registro['ficha']
                    )

                    aprendiz = Aprendiz.objects.filter(
                        documento=registro['documento']
                    ).first()

                    if not aprendiz:
                        omitidos += 1
                        errores_detallados.append(
                            f"Fila {registro['fila_excel']}: Aprendiz no existe"
                        )
                        continue

                    aprendiz.ficha = ficha
                    aprendiz.save()

                    Inasistencia.objects.update_or_create(
                        aprendiz=aprendiz,
                        fecha=registro['fecha'],
                        defaults={
                            'justificada': registro['justificada'],
                            'importado_desde_excel': True,
                            'archivo_origen': archivo_importado,
                        }
                    )

                    importados += 1

            archivo_importado.estado = 'COMPLETADO'
            archivo_importado.registros_importados = importados
            archivo_importado.registros_omitidos = omitidos
            archivo_importado.registros_error = len(errores_detallados)
            archivo_importado.log_errores = '\n'.join(errores_detallados)
            archivo_importado.save()

            messages.success(request, f"✅ Importación finalizada: {importados} registros")

            return redirect('importador:historial')

        except Exception as e:
            archivo_importado.estado = 'ERROR'
            archivo_importado.log_errores = str(e)
            archivo_importado.save()
            messages.error(request, f"❌ Error: {str(e)}")

    return render(request, 'importador/importar_inasistencias.html')


# ✅ =========================
# ✅ IMPORTAR EVALUACIONES
# ✅ =========================
@login_required
def importar_evaluaciones(request):

    if request.method == 'POST':
        form = ImportarEvaluacionesForm(request.POST, request.FILES)

        if form.is_valid():
            archivo_excel = request.FILES['archivo']

            timestamp = int(time.time())
            filename = f"evaluaciones_{timestamp}_{archivo_excel.name}"
            filepath = os.path.join(settings.EXCEL_UPLOAD_DIR, filename)

            with open(filepath, 'wb+') as destination:
                for chunk in archivo_excel.chunks():
                    destination.write(chunk)

            try:
                inicio = time.time()
                parser = ExcelParser(filepath)

                if not parser.load_file():
                    raise Exception("No se pudo cargar el archivo")

                # ✅ OBTENER FICHA DESDE EXCEL
                numero_ficha = parser.get_ficha_from_excel()
                ficha, creada = Ficha.objects.get_or_create(numero=numero_ficha)

                archivo_importado = ArchivoImportado.objects.create(
                    tipo='EVALUACIONES',
                    archivo=archivo_excel,
                    usuario=request.user,
                    ficha=ficha,
                    estado='PROCESANDO'
                )

                columnas_detectadas = parser.detect_columns_evaluaciones()

                if not all([
                    columnas_detectadas.get('documento'),
                    columnas_detectadas.get('resultado_aprendizaje'),
                    columnas_detectadas.get('juicio')
                ]):
                    raise Exception("Faltan columnas obligatorias")

                registros, errores = parser.parse_evaluaciones()

                importados = 0
                omitidos = 0
                errores_detallados = []

                with transaction.atomic():
                    for registro in registros:
                        try:
                            aprendiz = Aprendiz.objects.filter(
                                documento=registro['documento'],
                                ficha=ficha
                            ).first()

                            if not aprendiz:
                                omitidos += 1
                                continue

                            ra = ResultadoAprendizaje.objects.filter(
                                codigo=registro['ra_codigo']
                            ).first()

                            if not ra:
                                omitidos += 1
                                continue

                            JuicioEvaluativo.objects.update_or_create(
                                aprendiz=aprendiz,
                                resultado_aprendizaje=ra,
                                fecha_evaluacion=timezone.now().date(),
                                defaults={
                                    'juicio': registro['juicio'],
                                    'importado_desde_excel': True,
                                    'archivo_origen': archivo_importado,
                                }
                            )

                            importados += 1

                        except Exception as e:
                            errores_detallados.append(str(e))

                fin = time.time()

                archivo_importado.estado = 'COMPLETADO'
                archivo_importado.registros_importados = importados
                archivo_importado.registros_omitidos = omitidos
                archivo_importado.registros_error = len(errores_detallados)
                archivo_importado.tiempo_proceso = fin - inicio
                archivo_importado.log_errores = '\n'.join(errores_detallados)
                archivo_importado.save()

                messages.success(
                    request,
                    f'✅ Evaluaciones importadas correctamente | Ficha {ficha.numero}'
                )

                return redirect('importador:historial')

            except Exception as e:
                messages.error(request, f'❌ Error: {str(e)}')
                logger.error(e, exc_info=True)

    else:
        form = ImportarEvaluacionesForm()

    return render(request, 'importador/importar_evaluaciones.html', {'form': form})


# ✅ =========================
# ✅ HISTORIAL Y DETALLE
# ✅ =========================
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
        messages.error(request, "No tienes permiso")
        return redirect('importador:historial')

    return render(request, 'importador/detalle.html', {'archivo': archivo})


def descargar_plantilla(request, tipo):
    return HttpResponse(f"Descarga de plantilla para {tipo}")
