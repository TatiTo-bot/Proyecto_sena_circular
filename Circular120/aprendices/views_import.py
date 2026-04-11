# aprendices/views_import.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from tablib import Dataset
from .models import Aprendiz, Ficha, Inasistencia
from .resources import AprendizJuiciosResource
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


# ══════════════════════════════════════════════════════════════════
#  IMPORTAR JUICIOS / APRENDICES
# ══════════════════════════════════════════════════════════════════

@login_required
def import_excel(request):
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            archivo = request.FILES['file']

            if archivo.name.endswith('.csv'):
                dataset = Dataset().load(archivo.read().decode('utf-8'), format='csv')
            elif archivo.name.endswith('.xlsx'):
                dataset = Dataset().load(archivo.read(), format='xlsx')
            elif archivo.name.endswith('.xls'):
                dataset = Dataset().load(archivo.read(), format='xls')
            else:
                messages.error(request, 'Formato no soportado.')
                return redirect('import_excel')

            info_encabezado = extraer_info_encabezado(dataset)

            ficha_obj = None
            if info_encabezado.get('ficha'):
                ficha_obj, created = Ficha.objects.get_or_create(
                    numero=info_encabezado['ficha'],
                    defaults={
                        'programa': info_encabezado.get('programa', 'Por definir'),
                        'fecha_inicio': info_encabezado.get('fecha_inicio'),
                        'fecha_fin': info_encabezado.get('fecha_fin'),
                    }
                )
                if not created:
                    if info_encabezado.get('programa'):
                        ficha_obj.programa = info_encabezado['programa']
                    if info_encabezado.get('fecha_inicio'):
                        ficha_obj.fecha_inicio = info_encabezado['fecha_inicio']
                    if info_encabezado.get('fecha_fin'):
                        ficha_obj.fecha_fin = info_encabezado['fecha_fin']
                    ficha_obj.save()
                messages.success(request,
                    f"✅ Ficha {info_encabezado['ficha']} procesada. "
                    f"Inicio: {info_encabezado.get('fecha_inicio') or 'N/A'}, "
                    f"Fin: {info_encabezado.get('fecha_fin') or 'N/A'}"
                )
            else:
                messages.warning(request, '⚠️ No se detectó número de ficha en el archivo')

            fila_inicio = encontrar_fila_datos(dataset)
            headers = list(dataset[fila_inicio])
            datos = dataset[fila_inicio + 1:]

            agregar_ficha        = 'Ficha' not in headers
            agregar_fecha_inicio = 'Fecha Inicio' not in headers
            agregar_fecha_fin    = 'Fecha Fin' not in headers

            if agregar_ficha:        headers.append('Ficha')
            if agregar_fecha_inicio: headers.append('Fecha Inicio')
            if agregar_fecha_fin:    headers.append('Fecha Fin')

            dataset_limpio = Dataset(headers=headers)
            ficha_num        = info_encabezado.get('ficha', '')
            fecha_inicio_val = str(info_encabezado.get('fecha_inicio', '') or '')
            fecha_fin_val    = str(info_encabezado.get('fecha_fin', '') or '')

            for row in datos:
                row_list = list(row)
                if agregar_ficha:        row_list.append(ficha_num)
                if agregar_fecha_inicio: row_list.append(fecha_inicio_val)
                if agregar_fecha_fin:    row_list.append(fecha_fin_val)
                dataset_limpio.append(row_list)

            resource = AprendizJuiciosResource()
            resource._ficha_numero = info_encabezado.get('ficha')
            result = resource.import_data(dataset_limpio, dry_run=False, raise_errors=False)

            if result.has_errors():
                errores = [f"Fila {r[0]}: {r[1]}" for r in result.row_errors()]
                messages.error(request, f"❌ Errores: {'; '.join(errores[:5])}")
            else:
                messages.success(request,
                    f"✅ Importación exitosa: {result.totals['new']} nuevos, "
                    f"{result.totals['update']} actualizados, "
                    f"{result.totals['skip']} omitidos"
                )

            if ficha_obj and (info_encabezado.get('fecha_inicio') or info_encabezado.get('fecha_fin')):
                actualizados = actualizar_fechas_aprendices(
                    ficha_obj,
                    info_encabezado.get('fecha_inicio'),
                    info_encabezado.get('fecha_fin')
                )
                if actualizados:
                    messages.info(request, f"📅 Fechas actualizadas en {actualizados} aprendices.")

            return redirect('aprendiz_list')

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messages.error(request, f'❌ Error: {str(e)}')
            return redirect('import_excel')

    return render(request, 'aprendices/import_excel.html')


# ══════════════════════════════════════════════════════════════════
#  IMPORTAR INASISTENCIAS — estructura real del Excel SENA
#
#  Estructura verificada del archivo real:
#    Col 0  → FICHA  ("1963009 - SUPERVISION DE LABORES MINERAS")
#    Col 13 → CC DEL APRENDIZ ("CC - 1075544961")
#    Col 17 → NOMBRE DEL APRENDIZ
#    Col 23 → FECHA INICIO  ("10/27/2025")
#    Col 24 → FECHA FIN     ("10/31/2025")
#    Col 25 → CANT. HORAS
#    Col 27 → JUSTIFICACION
#
#  Fila 0 = título, Fila 1 = encabezados, Fila 2+ = datos
# ══════════════════════════════════════════════════════════════════

# Índices de columna verificados con el archivo real
COL_FICHA   = 0
COL_DOC     = 13
COL_NOMBRE  = 17
COL_FI      = 23
COL_FF      = 24
COL_JUSTIF  = 27

PALABRAS_JUSTIFICADAS = [
    'JUSTIFICABLE', 'JUSTIFICADO', 'ENFERMEDAD', 'CALAMIDAD',
    'PRESENTACION', 'PRESENTACIÓN', 'CORREO', 'MÉDICO', 'MEDICO',
    'FORMULA', 'FÓRMULA', 'INCAPACIDAD', 'EJERCITO', 'EJÉRCITO',
]

PALABRAS_INASISTENCIAS = [
    'consolidado de inasistencias', 'justificacion',
    'justificación', 'cant. horas', 'cant horas',
]


@login_required
def import_inasistencias(request):
    """Importa el Excel consolidado de inasistencias del SENA"""
    if request.method != 'POST' or not request.FILES.get('file'):
        return render(request, 'aprendices/import_inasistencias.html')

    try:
        archivo = request.FILES['file']
        ext = archivo.name.lower().split('.')[-1]

        # ── Convertir a filas usando LibreOffice (soporta .xls real) ──
        filas = _leer_excel_como_filas(archivo, ext)

        if not filas:
            messages.error(request, '❌ No se pudo leer el archivo.')
            return redirect('import_inasistencias')

        creadas  = 0
        omitidas = 0
        sin_aprendiz = 0

        # Filas de datos empiezan en índice 2 (0=título, 1=encabezados)
        for fila in filas[2:]:
            try:
                if len(fila) <= COL_DOC:
                    omitidas += 1
                    continue

                # ── Documento ──────────────────────────────────────────
                doc_raw = _str(fila, COL_DOC)
                if not doc_raw:
                    omitidas += 1
                    continue

                # Limpiar "CC - 1075544961" → "1075544961"
                doc = doc_raw.upper()
                for p in ['CC -', 'CC-', 'C.C.', 'CC']:
                    doc = doc.replace(p, '')
                doc = doc.strip().replace('.', '').replace(' ', '').replace(',', '')
                if doc.endswith('.0'):
                    doc = doc[:-2]

                if not doc or not any(c.isdigit() for c in doc):
                    omitidas += 1
                    continue

                # ── Buscar aprendiz ────────────────────────────────────
                try:
                    aprendiz = Aprendiz.objects.get(documento=doc)
                except Aprendiz.DoesNotExist:
                    sin_aprendiz += 1
                    continue

                # ── Fecha (preferir fecha fin) ─────────────────────────
                fecha = _fecha(_raw(fila, COL_FF)) or _fecha(_raw(fila, COL_FI))
                if not fecha:
                    omitidas += 1
                    continue

                # ── Ficha ──────────────────────────────────────────────
                ficha_obj = aprendiz.ficha
                ficha_raw = _str(fila, COL_FICHA)
                if ficha_raw:
                    num = ficha_raw.split('-')[0].strip().split(' ')[0].strip()
                    if num.isdigit():
                        f = Ficha.objects.filter(numero=num).first()
                        if f:
                            ficha_obj = f

                if not ficha_obj:
                    omitidas += 1
                    continue

                # ── Justificación ──────────────────────────────────────
                justif_raw = _str(fila, COL_JUSTIF).upper()
                motivo     = justif_raw or 'SIN JUSTIFICACIÓN'
                justificada = any(p in justif_raw for p in PALABRAS_JUSTIFICADAS)

                # ── Crear (evitar duplicados) ──────────────────────────
                _, created = Inasistencia.objects.get_or_create(
                    aprendiz=aprendiz,
                    fecha=fecha,
                    defaults={
                        'ficha':       ficha_obj,
                        'justificada': justificada,
                        'motivo':      motivo[:500],
                    }
                )
                if created:
                    creadas += 1
                else:
                    omitidas += 1

            except Exception as e:
                omitidas += 1
                continue

        # ── Mensajes ───────────────────────────────────────────────────
        if creadas:
            messages.success(request, f'✅ {creadas} inasistencias importadas correctamente.')
        else:
            messages.warning(request, '⚠️ No se importaron inasistencias nuevas.')

        if sin_aprendiz:
            messages.info(request,
                f'ℹ️ {sin_aprendiz} filas omitidas porque el aprendiz no existe en el sistema. '
                f'Primero sube el Excel de juicios para registrar los aprendices.'
            )
        if omitidas:
            messages.info(request,
                f'ℹ️ {omitidas} filas omitidas (sin fecha, sin ficha, o duplicadas).'
            )

        return redirect('inasistencia_list')

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        messages.error(request, f'❌ Error al procesar archivo: {str(e)}')
        return redirect('import_inasistencias')


# ══════════════════════════════════════════════════════════════════
#  DETECCIÓN AUTOMÁTICA EN FileUploadView
# ══════════════════════════════════════════════════════════════════

def es_excel_inasistencias_OLD(archivo):
    """
    Lee las primeras filas del archivo y detecta si es el
    Consolidado de Inasistencias del SENA buscando palabras clave.
    """
    try:
        archivo.seek(0)
        contenido = archivo.read(8000)
        archivo.seek(0)

        texto = ''
        try:
            texto = contenido.decode('latin-1').lower()
        except Exception:
            texto = str(contenido).lower()

        return any(p in texto for p in PALABRAS_INASISTENCIAS)
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════
#  UTILIDADES INTERNAS
# ══════════════════════════════════════════════════════════════════

def _leer_excel_como_filas(archivo, ext):
    """Convierte el archivo Excel a lista de listas usando LibreOffice."""
    import subprocess, os, tempfile, csv

    # Guardar en temp
    tmp = tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False)
    for chunk in archivo.chunks():
        tmp.write(chunk)
    tmp.close()

    csv_path = None
    try:
        # Convertir a CSV con LibreOffice
        out_dir = tempfile.mkdtemp()
        r = subprocess.run([
            'libreoffice', '--headless', '--convert-to', 'csv',
            '--outdir', out_dir, tmp.name
        ], capture_output=True, timeout=30)

        csv_files = [f for f in os.listdir(out_dir) if f.endswith('.csv')]
        if not csv_files:
            return []

        csv_path = os.path.join(out_dir, csv_files[0])

        filas = []
        with open(csv_path, encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            for row in reader:
                filas.append(row)
        return filas

    except Exception as e:
        print(f"Error leyendo Excel: {e}")
        return []
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        if csv_path:
            try:
                os.unlink(csv_path)
            except Exception:
                pass


def _raw(fila, idx):
    try:
        return fila[idx] if idx < len(fila) else None
    except (IndexError, TypeError):
        return None


def _str(fila, idx):
    v = _raw(fila, idx)
    return str(v).strip() if v is not None else ''


def _fecha(valor):
    """Parsea una fecha desde string o número."""
    if not valor:
        return None
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return valor
    if isinstance(valor, datetime):
        return valor.date()
    valor_str = str(valor).strip()
    if not valor_str or valor_str.lower() in ('none', 'nan', ''):
        return None

    formatos = [
        '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d',
        '%d-%m-%Y', '%d/%m/%y', '%Y/%m/%d',
        '%d.%m.%Y', '%m/%d/%y',
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(valor_str[:10], fmt).date()
        except ValueError:
            continue
    return None


def extraer_info_encabezado(dataset):
    info = {'ficha': None, 'programa': None, 'fecha_inicio': None, 'fecha_fin': None}
    for i in range(min(15, len(dataset))):
        row = dataset[i]
        for j, valor in enumerate(row):
            if not valor:
                continue
            valor_str = str(valor).strip()
            if not info['ficha']:
                if 'ficha' in valor_str.lower() and 'caracterización' in valor_str.lower():
                    for k in range(j + 1, min(j + 5, len(row))):
                        if row[k]:
                            numero = str(row[k]).strip().split('.')[0]
                            if 6 <= len(numero) <= 8 and numero.isdigit():
                                info['ficha'] = numero
                                break
                elif 6 <= len(valor_str) <= 8 and valor_str.split('.')[0].isdigit():
                    info['ficha'] = valor_str.split('.')[0]
            if not info['programa']:
                if 'denominación' in valor_str.lower() or 'denominacion' in valor_str.lower():
                    for k in range(j + 1, min(j + 10, len(row))):
                        if row[k] and len(str(row[k]).strip()) > 10:
                            info['programa'] = str(row[k]).strip()
                            break
            if not info['fecha_inicio']:
                if 'fecha inicio' in valor_str.lower():
                    for k in range(j + 1, min(j + 5, len(row))):
                        f = _fecha(row[k])
                        if f:
                            info['fecha_inicio'] = f
                            break
            if not info['fecha_fin']:
                if 'fecha fin' in valor_str.lower() and 'inicio' not in valor_str.lower():
                    for k in range(j + 1, min(j + 5, len(row))):
                        f = _fecha(row[k])
                        if f:
                            info['fecha_fin'] = f
                            break
    return info


def encontrar_fila_datos(dataset):
    keywords = ['documento', 'número', 'nombre', 'apellido', 'competencia']
    for i in range(min(25, len(dataset))):
        row_str = ' '.join([str(v).lower() for v in dataset[i] if v])
        if sum(1 for kw in keywords if kw in row_str) >= 3:
            return i
    return 0


def actualizar_fechas_aprendices(ficha, fecha_inicio, fecha_fin):
    aprendices = Aprendiz.objects.filter(ficha=ficha)
    actualizados = 0
    for aprendiz in aprendices:
        cambios = []
        if fecha_inicio and not aprendiz.fecha_inicio:
            aprendiz.fecha_inicio = fecha_inicio
            cambios.append('fecha_inicio')
        if fecha_fin:
            fecha_base = aprendiz.fecha_final or fecha_fin
            if not aprendiz.fecha_final:
                aprendiz.fecha_final = fecha_fin
                cambios.append('fecha_final')
            if not aprendiz.fecha_fin_productiva:
                aprendiz.fecha_fin_productiva = fecha_base
                cambios.append('fecha_fin_productiva')
            if not aprendiz.fecha_fin_lectiva:
                aprendiz.fecha_fin_lectiva = fecha_base - relativedelta(months=6)
                cambios.append('fecha_fin_lectiva')
        if cambios:
            aprendiz.save(update_fields=cambios)
            actualizados += 1
    return actualizados


def es_excel_inasistencias(archivo):
    """
    Detecta si el archivo es el Consolidado de Inasistencias del SENA.
    Busca en los bytes crudos (sin lowercase) porque el XLS los guarda en MAYÚSCULAS.
    """
    try:
        archivo.seek(0)
        contenido = archivo.read(20000)
        archivo.seek(0)

        # Estos patrones están en MAYÚSCULAS en el archivo XLS binario
        PATRONES = [
            b'JUSTIFICACION',
            b'INASISTENCIA',
            b'CANT. HORAS',
        ]
        return any(p in contenido for p in PATRONES)

    except Exception:
        return False