# aprendices/management/commands/import_consolidado.py
import os
import glob
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date
from aprendices.models import Aprendiz, Ficha, Inasistencia, Competencia, ResultadoAprendizaje, AprendizResultado

def choose_col(colmap, *cands):
    lower_map = {k.lower(): k for k in colmap}
    for c in cands:
        k = c.lower()
        if k in lower_map:
            return lower_map[k]
    return None

class Command(BaseCommand):
    help = 'Importa inasistencias y juicios evaluativos desde uno o varios Excel. Acepta ruta a archivo o carpeta.'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='Ruta al archivo Excel, o carpeta con *.xls, *.xlsx')

    def handle(self, *args, **options):
        path = options['path']
        files = []
        if os.path.isdir(path):
            files = glob.glob(os.path.join(path, '*.xls')) + glob.glob(os.path.join(path, '*.xlsx'))
        else:
            if any(c in path for c in ['*','?']):
                files = glob.glob(path)
            else:
                files = [path]

        files = [f for f in files if os.path.exists(f)]
        if not files:
            self.stdout.write(self.style.ERROR(f'No se encontró archivo(s) en: {path}'))
            return

        total_inas = 0
        total_resultados = 0
        for fpath in files:
            self.stdout.write(f'Procesando: {fpath}')
            try:
                df = pd.read_excel(fpath, dtype=str)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error leyendo {fpath}: {e}'))
                continue

            colmap = {c: c for c in df.columns}
            cols_lower = [c.lower() for c in df.columns]

            tiene_resultado = any(x in cols_lower for x in ['resultado','juicio','juicio evaluativo','estado','aprobado','no aprobado','nota','resultado_aprendizaje','ra'])
            tiene_inasistencia = any(x in cols_lower for x in ['fecha','inasistencia','motivo','justificada','fecha inasistencia','fecha_asistencia'])

            if tiene_inasistencia:
                self.stdout.write(' -> Detectado formato: INASISTENCIAS (o mixto)')
                col_doc = choose_col(colmap, 'documento','cedula','identificacion','identificación','doc','num_identificacion')
                col_ficha = choose_col(colmap, 'ficha','numero ficha','numero_ficha','numero','ficha_numero','número ficha')
                col_fecha = choose_col(colmap, 'fecha','fecha inasistencia','fecha_inasistencia','fecha de inasistencia','fecha_asistencia')
                col_motivo = choose_col(colmap, 'motivo','observacion','razon','justificacion','razón')

                created = 0
                skipped = 0
                with transaction.atomic():
                    for idx, row in df.iterrows():
                        doc = str(row.get(col_doc) or '').strip()
                        ficha_num = str(row.get(col_ficha) or '').strip()
                        fecha_raw = row.get(col_fecha)
                        motivo = row.get(col_motivo) or ''

                        if not doc or not ficha_num:
                            skipped += 1
                            continue

                        fecha = None
                        try:
                            if pd.isna(fecha_raw):
                                fecha = None
                            else:
                                if isinstance(fecha_raw, pd.Timestamp):
                                    fecha = fecha_raw.date()
                                else:
                                    fecha = parse_date(str(fecha_raw))
                        except Exception:
                            fecha = None

                        aprendiz, _ = Aprendiz.objects.get_or_create(documento=doc, defaults={'nombre':'Desconocido','apellido':''})
                        ficha, _ = Ficha.objects.get_or_create(numero=ficha_num)

                        if fecha:
                            Inasistencia.objects.create(
                                aprendiz=aprendiz,
                                ficha=ficha,
                                fecha=fecha,
                                justificada=False,
                                motivo=str(motivo)[:1000],
                                reportado_por=''
                            )
                            created += 1
                        else:
                            skipped += 1

                self.stdout.write(self.style.SUCCESS(f'Inasistencias creadas desde {os.path.basename(fpath)}: {created}, omitidas: {skipped}'))
                total_inas += created

            if tiene_resultado:
                self.stdout.write(' -> Detectado formato: JUICIOS EVALUATIVOS / RESULTADOS')
                col_doc = choose_col(colmap, 'documento','cedula','identificacion','identificación','doc')
                col_comp = choose_col(colmap, 'competencia','codigo competencia','cod_comp','cod_competencia','competencia_codigo')
                col_ra = choose_col(colmap, 'resultado','resultado aprendizaje','ra','codigo resultado','resultado_codigo','resultado_aprendizaje','codigo_ra')
                col_estado = choose_col(colmap, 'estado','juicio','juicio evaluativo','aprobado','estado resultado','resultado')
                col_nombre = choose_col(colmap, 'nombre','nombres','aprendiz_nombre','aprendiz','nombre_aprendiz')

                created_res = 0
                skipped_res = 0
                with transaction.atomic():
                    for idx, row in df.iterrows():
                        doc = str(row.get(col_doc) or '').strip()
                        comp_code = str(row.get(col_comp) or '').strip()
                        ra_code = str(row.get(col_ra) or '').strip()
                        estado = str(row.get(col_estado) or '').strip()
                        nombre = str(row.get(col_nombre) or '').strip()

                        if not doc:
                            skipped_res += 1
                            continue

                        aprendiz, _ = Aprendiz.objects.get_or_create(documento=doc, defaults={'nombre': nombre or 'Desconocido','apellido':''})

                        if ra_code:
                            ra_name = ra_code
                            competencia = None
                            if comp_code:
                                competencia, _ = Competencia.objects.get_or_create(codigo=comp_code, defaults={'nombre': comp_code})
                            ra_obj, created = ResultadoAprendizaje.objects.get_or_create(
                                codigo=ra_code,
                                defaults={'nombre': ra_name, 'competencia': competencia}
                            )
                            estado_norm = 'PENDIENTE'
                            if estado:
                                e = estado.lower()
                                if 'aprob' in e or 'apto' in e or 'satisfactorio' in e:
                                    estado_norm = 'APROBADO'
                                elif 'no' in e or 'rechaz' in e or 'no aprobado' in e:
                                    estado_norm = 'NO_APROBADO'
                            # crear AprendizResultado
                            ar, created_ar = AprendizResultado.objects.get_or_create(
                                aprendiz=aprendiz,
                                resultado=ra_obj,
                                defaults={'estado': estado_norm}
                            )
                            if not created_ar:
                                ar.estado = estado_norm
                                ar.save()
                            created_res += 1
                        else:
                            # si no hay RA, usar competencia + estado en observaciones
                            if comp_code and estado:
                                competencia, _ = Competencia.objects.get_or_create(codigo=comp_code, defaults={'nombre': comp_code})
                                aprendiz.observaciones = (aprendiz.observaciones or '') + f"\nComp {comp_code}: {estado}"
                                aprendiz.save()
                                created_res += 1
                            else:
                                skipped_res += 1

                self.stdout.write(self.style.SUCCESS(f'Resultados procesados desde {os.path.basename(fpath)}: {created_res}, omitidos: {skipped_res}'))
                total_resultados += created_res

        self.stdout.write(self.style.SUCCESS(f'Import completo. Total inasistencias: {total_inas}. Total resultados: {total_resultados}'))
