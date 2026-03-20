# VERSIÓN ARREGLADA - Crea la ficha y actualiza aprendices

import os
import glob
import pandas as pd
from datetime import datetime, date
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date
from aprendices.models import Aprendiz, Ficha, Inasistencia, Competencia, ResultadoAprendizaje, AprendizResultado

def choose_col(colmap, *cands):
    lower_map = {k.lower().strip(): k for k in colmap}
    for c in cands:
        k = c.lower().strip()
        if k in lower_map:
            return lower_map[k]
        for map_key, map_val in lower_map.items():
            if k in map_key:
                return map_val
    return None

def normalizar_documento(doc):
    if pd.isna(doc) or doc is None:
        return None
    doc_str = str(doc).strip()
    doc_str = doc_str.replace('.', '').replace(',', '').replace(' ', '')
    if doc_str.endswith('.0'):
        doc_str = doc_str[:-2]
    return doc_str if doc_str else None

def extraer_info_simple(df_raw, stdout):
    info = {'ficha': None, 'programa': None}
    
    stdout.write('   🔍 Extrayendo información...')
    
    for fila in range(min(15, len(df_raw))):
        for col in range(min(15, len(df_raw.columns))):
            valor = df_raw.iloc[fila, col]
            
            if pd.isna(valor):
                continue
            
            valor_str = str(valor).strip()
            
            # FICHA - Buscar "Ficha de Caracterización:"
            if not info['ficha']:
                if 'ficha de caracterización' in valor_str.lower() or 'ficha de caracterizacion' in valor_str.lower():
                    # El valor está en la columna siguiente (B tiene etiqueta, C tiene valor)
                    for col_sig in range(col + 1, min(col + 5, len(df_raw.columns))):
                        ficha_val = df_raw.iloc[fila, col_sig]
                        if pd.notna(ficha_val):
                            ficha_str = str(ficha_val).strip()
                            if len(ficha_str) >= 6 and len(ficha_str) <= 8 and ficha_str.isdigit():
                                info['ficha'] = ficha_str
                                stdout.write(f'   ✅ Ficha: {ficha_str}')
                                break
                # También buscar números de ficha sueltos
                elif len(valor_str) >= 6 and len(valor_str) <= 8 and valor_str.isdigit():
                    if not info['ficha']:
                        info['ficha'] = valor_str
                        stdout.write(f'   ✅ Ficha: {valor_str}')
            
            # PROGRAMA - Buscar "Denominación:"
            if not info['programa']:
                if 'denominación:' in valor_str.lower() or 'denominacion:' in valor_str.lower():
                    # Buscar en las columnas siguientes de la MISMA fila
                    for col_sig in range(col + 1, min(col + 10, len(df_raw.columns))):
                        prog_val = df_raw.iloc[fila, col_sig]
                        if pd.notna(prog_val):
                            prog_str = str(prog_val).strip()
                            if len(prog_str) > 10:
                                info['programa'] = prog_str
                                stdout.write(f'   ✅ Programa: {prog_str[:80]}')
                                break
                # Buscar textos largos relacionados con programas
                elif len(valor_str) > 30:
                    palabras_clave = ['gestion', 'gestión', 'tecnolog', 'tecnic', 'software', 
                                     'desarrollo', 'analisis', 'análisis', 'sistemas', 
                                     'administrativo', 'salud', 'servicio', 'seguridad']
                    if any(palabra in valor_str.lower() for palabra in palabras_clave):
                        # Evitar que tome resultados de aprendizaje
                        if 'resultado' not in valor_str.lower() and 'competencia' not in valor_str.lower():
                            info['programa'] = valor_str
                            stdout.write(f'   ✅ Programa: {valor_str[:80]}')
    
    return info

def detectar_fila_inicio(df):
    keywords = ['documento', 'nombre', 'apellido', 'competencia', 'resultado', 'juicio']
    for idx in range(min(25, len(df))):
        row_lower = [str(v).lower() for v in df.iloc[idx].values if pd.notna(v)]
        matches = sum(1 for kw in keywords if any(kw in cell for cell in row_lower))
        if matches >= 3:
            return idx
    return 0

class Command(BaseCommand):
    help = 'Importa datos'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str)

    def handle(self, *args, **options):
        path = options['path']
        files = [path] if os.path.exists(path) else []
        if os.path.isdir(path):
            files = glob.glob(os.path.join(path, '*.xls')) + glob.glob(os.path.join(path, '*.xlsx'))

        if not files:
            self.stdout.write('No hay archivos')
            return

        stats = {'juicios': 0, 'aprendices': 0, 'fichas': 0, 'actualizados': 0}

        for fpath in files:
            self.stdout.write(f'\n📄 {os.path.basename(fpath)}')
            
            try:
                df_raw = pd.read_excel(fpath, header=None)
                info_enc = extraer_info_simple(df_raw, self.stdout)
                
                fila = detectar_fila_inicio(df_raw)
                df = pd.read_excel(fpath, header=fila, dtype=str)
                self.stdout.write(f'   ✓ {len(df)} registros')
                
            except Exception as e:
                self.stdout.write(f'   ❌ {e}')
                continue

            colmap = {c: c for c in df.columns}
            cols_lower = [str(c).lower() for c in df.columns]

            tiene_resultado = any(x in cols_lower for x in ['resultado', 'juicio', 'competencia'])

            if tiene_resultado:
                self.stdout.write('   🔹 JUICIOS')
                
                col_doc = choose_col(colmap, 'numero de documento', 'número', 'documento')
                col_nombre = choose_col(colmap, 'nombre')
                col_apellido = choose_col(colmap, 'apellido')
                col_comp = choose_col(colmap, 'competencia')
                col_ra = choose_col(colmap, 'resultado de aprendizaje', 'resultado')
                col_juicio = choose_col(colmap, 'juicio de evaluacion', 'juicio')
                
                if not col_doc:
                    continue

                # CREAR FICHA PRIMERO
                ficha_obj = None
                if info_enc['ficha']:
                    ficha_obj, created_fi = Ficha.objects.get_or_create(
                        numero=info_enc['ficha'],
                        defaults={'programa': info_enc['programa'] or 'Por definir'}
                    )
                    
                    # ACTUALIZAR el programa si se detectó y la ficha no lo tiene
                    if info_enc['programa']:
                        if not ficha_obj.programa or ficha_obj.programa == 'Por definir':
                            ficha_obj.programa = info_enc['programa']
                            ficha_obj.save()
                            self.stdout.write(f'   ✅ Programa actualizado: {info_enc["programa"][:60]}')
                    
                    if created_fi:
                        stats['fichas'] += 1
                        self.stdout.write(f'   ✅ Ficha {info_enc["ficha"]} creada')
                    else:
                        self.stdout.write(f'   ✅ Ficha {info_enc["ficha"]} ya existe')

                docs_procesados = []
                creados = 0
                
                with transaction.atomic():
                    for idx, row in df.iterrows():
                        try:
                            doc = normalizar_documento(row.get(col_doc))
                            if not doc or len(doc) < 4:
                                continue

                            docs_procesados.append(doc)
                            nombre = str(row.get(col_nombre) or 'Por actualizar').strip() if col_nombre else 'Por actualizar'
                            apellido = str(row.get(col_apellido) or '').strip() if col_apellido else ''

                            # CREAR APRENDIZ CON FICHA
                            aprendiz, created = Aprendiz.objects.get_or_create(
                                documento=doc,
                                defaults={
                                    'nombre': nombre, 
                                    'apellido': apellido, 
                                    'estado_formacion': 'EN_FORMACION',
                                    'ficha': ficha_obj  # ASIGNAR FICHA AQUÍ
                                }
                            )
                            
                            # Si ya existe, actualizar SIEMPRE la ficha
                            if not created:
                                if nombre != 'Por actualizar':
                                    aprendiz.nombre = nombre
                                    aprendiz.apellido = apellido
                                # SIEMPRE actualizar la ficha al importar
                                aprendiz.ficha = ficha_obj
                                aprendiz.save()
                            else:
                                stats['aprendices'] += 1

                            # Juicios
                            comp_code = str(row.get(col_comp) or '').strip() if col_comp else None
                            ra_text = str(row.get(col_ra) or '').strip() if col_ra else None
                            juicio_text = str(row.get(col_juicio) or '').strip() if col_juicio else ''

                            if not ra_text or len(ra_text) < 5:
                                continue

                            ra_code = ra_text.split('-')[0].split(':')[0].strip()

                            competencia = None
                            if comp_code:
                                competencia, _ = Competencia.objects.get_or_create(
                                    codigo=comp_code, defaults={'nombre': comp_code}
                                )

                            ra_obj, _ = ResultadoAprendizaje.objects.get_or_create(
                                codigo=ra_code,
                                defaults={'nombre': ra_text[:200], 'competencia': competencia}
                            )

                            estado = 'PENDIENTE'
                            if juicio_text:
                                j = juicio_text.lower()
                                if 'aprob' in j:
                                    estado = 'APROBADO'
                                elif 'evaluar' in j:
                                    estado = 'PENDIENTE'

                            AprendizResultado.objects.update_or_create(
                                aprendiz=aprendiz, resultado=ra_obj,
                                defaults={'estado': estado, 'fecha': date.today()}
                            )
                            creados += 1
                        except:
                            pass

                self.stdout.write(f'   ✓ {creados} juicios')
                stats['juicios'] += creados

        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'📋 Juicios: {stats["juicios"]}')
        self.stdout.write(f'👥 Aprendices: {stats["aprendices"]} | Fichas: {stats["fichas"]}')
        self.stdout.write('='*60)