from import_export import resources, fields, widgets
from import_export.widgets import ForeignKeyWidget
from .models import Aprendiz, Ficha, Competencia, ResultadoAprendizaje, AprendizResultado
from datetime import date, datetime


class SafeDateWidget(widgets.Widget):
    """Widget que maneja múltiples formatos de fecha del Excel del SENA"""

    def clean(self, value, row=None, **kwargs):
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, (int, float)):
            if 10000 < value < 100000:
                from datetime import timedelta
                base = datetime(1899, 12, 30)
                return (base + timedelta(days=int(value))).date()
            return None
        valor_str = str(value).strip()
        if not valor_str or valor_str in ('None', 'nan', ''):
            return None
        formatos = [
            '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y',
            '%d/%m/%y', '%d-%m-%y', '%Y/%m/%d',
            '%m/%d/%Y', '%d.%m.%Y',
        ]
        for fmt in formatos:
            try:
                return datetime.strptime(valor_str, fmt).date()
            except ValueError:
                continue
        return None

    def render(self, value, obj=None):
        if value:
            return value.strftime('%Y-%m-%d')
        return ''


# Mapa COMPLETO de estados del Excel SENA -> código interno del modelo
MAPA_ESTADO_SENA = {
    # Texto exacto visto en los Excel reales (en mayúsculas del SENA)
    'en formacion':       'EN_FORMACION',
    'en formación':       'EN_FORMACION',
    'etapa lectiva':      'ETAPA_LECTIVA',
    'etapa productiva':   'ETAPA_PRODUCTIVA',
    'por certificar':     'POR_CERTIFICAR',
    'certificado':        'CERTIFICADO',
    'cancelado':          'CANCELADO',
    'retiro voluntario':  'RETIRO_VOLUNTARIO',
    'aplazamiento':       'APLAZAMIENTO',
    'aplazado':           'APLAZAMIENTO',   # el SENA usa "APLAZADO"
    'trasladado':         'TRASLADADO',     # el SENA usa "TRASLADADO"
    'traslado':           'TRASLADADO',
}


class AprendizJuiciosResource(resources.ModelResource):
    """Resource para importar aprendices desde el Reporte de Juicios del SENA"""

    documento = fields.Field(
        column_name='Número de Documento',
        attribute='documento'
    )

    nombre = fields.Field(
        column_name='Nombre',
        attribute='nombre'
    )

    apellido = fields.Field(
        column_name='Apellido',
        attribute='apellido'
    )

    email = fields.Field(
        column_name='Email',
        attribute='email',
        saves_null_values=False
    )

    estado_formacion = fields.Field(
        column_name='Estado',
        attribute='estado_formacion'
    )

    fecha_inicio = fields.Field(
        column_name='Fecha Inicio',
        attribute='fecha_inicio',
        widget=SafeDateWidget()
    )

    fecha_final = fields.Field(
        column_name='Fecha Fin',
        attribute='fecha_final',
        widget=SafeDateWidget()
    )

    fecha_fin_lectiva = fields.Field(
        column_name='Fecha Fin Lectiva',
        attribute='fecha_fin_lectiva',
        widget=SafeDateWidget()
    )

    fecha_fin_productiva = fields.Field(
        column_name='Fecha Fin Productiva',
        attribute='fecha_fin_productiva',
        widget=SafeDateWidget()
    )

    ficha = fields.Field(
        column_name='Ficha',
        attribute='ficha',
        widget=ForeignKeyWidget(Ficha, 'numero')
    )

    class Meta:
        model = Aprendiz
        import_id_fields = ['documento']
        skip_unchanged = True
        report_skipped = True
        exclude = ("created_at", "updated_at")
        fields = (
            'documento', 'nombre', 'apellido', 'email',
            'estado_formacion',
            'fecha_inicio', 'fecha_final', 'fecha_fin_lectiva', 'fecha_fin_productiva',
            'ficha',
        )

    def before_import_row(self, row, **kwargs):
        """Normalizar datos antes de importar"""

        # ── Documento ─────────────────────────────────────────────────────
        for col in ('Número de Documento', 'Numero de Documento', 'Documento'):
            if row.get(col):
                doc = str(row[col]).strip()
                doc = doc.replace('.', '').replace(',', '').replace(' ', '')
                if doc.endswith('.0'):
                    doc = doc[:-2]
                row['Número de Documento'] = doc
                break

        # ── Nombre / Apellido  (el SENA a veces usa plural) ───────────────
        if not row.get('Nombre') and row.get('Nombres'):
            row['Nombre'] = row['Nombres']
        if not row.get('Apellido') and row.get('Apellidos'):
            row['Apellido'] = row['Apellidos']

        if not row.get('Nombre'):
            row['Nombre'] = 'Por actualizar'

        # ── Estado ────────────────────────────────────────────────────────
        # Convierte el texto libre del Excel al código interno del modelo.
        # Si el valor no está en el mapa se guarda TAL CUAL para no perder info.
        estado_raw = str(row.get('Estado', '') or '').strip()
        if estado_raw:
            codigo = MAPA_ESTADO_SENA.get(estado_raw.lower())
            if codigo:
                row['Estado'] = codigo
            else:
                # Valor desconocido: intentar usarlo directamente (ej. ya es 'EN_FORMACION')
                # Si no coincide con ningún choice Django lo rechazará con error de validación,
                # pero al menos no se pierde silenciosamente.
                row['Estado'] = estado_raw
        else:
            row['Estado'] = 'EN_FORMACION'   # default si viene vacío

        return row

    def after_import_row(self, row, row_result, **kwargs):
        """Asignar ficha y fechas, y procesar juicios evaluativos"""
        try:
            doc = row.get('Número de Documento')
            if not doc:
                return

            aprendiz = Aprendiz.objects.get(documento=doc)

            # ── Asignar ficha si no tiene ──────────────────────────────────
            ficha_numero = getattr(self, '_ficha_numero', None)
            if ficha_numero and not aprendiz.ficha_id:
                try:
                    aprendiz.ficha = Ficha.objects.get(numero=ficha_numero)
                    aprendiz.save(update_fields=['ficha'])
                except Ficha.DoesNotExist:
                    pass

            # ── Completar fechas desde la ficha si faltan ──────────────────
            ficha = aprendiz.ficha
            if ficha:
                cambios = []
                if not aprendiz.fecha_inicio and ficha.fecha_inicio:
                    aprendiz.fecha_inicio = ficha.fecha_inicio
                    cambios.append('fecha_inicio')
                if not aprendiz.fecha_final and ficha.fecha_fin:
                    aprendiz.fecha_final = ficha.fecha_fin
                    cambios.append('fecha_final')

                fecha_base = aprendiz.fecha_final
                if fecha_base:
                    if not aprendiz.fecha_fin_productiva:
                        aprendiz.fecha_fin_productiva = fecha_base
                        cambios.append('fecha_fin_productiva')
                    if not aprendiz.fecha_fin_lectiva:
                        from dateutil.relativedelta import relativedelta
                        aprendiz.fecha_fin_lectiva = fecha_base - relativedelta(months=6)
                        cambios.append('fecha_fin_lectiva')

                if cambios:
                    aprendiz.save(update_fields=cambios)

            # ── Juicios evaluativos ────────────────────────────────────────
            comp_codigo = (row.get('Competencia') or '').strip()
            ra_texto    = (row.get('Resultado de Aprendizaje') or '').strip()
            juicio_txt  = (row.get('Juicio de Evaluación') or '').strip()

            if ra_texto and len(ra_texto) >= 5:
                ra_codigo = ra_texto.split('-')[0].split(':')[0].strip()

                competencia = None
                if comp_codigo:
                    competencia, _ = Competencia.objects.get_or_create(
                        codigo=comp_codigo,
                        defaults={'nombre': comp_codigo}
                    )

                ra_obj, _ = ResultadoAprendizaje.objects.get_or_create(
                    codigo=ra_codigo,
                    defaults={'nombre': ra_texto[:500], 'competencia': competencia}
                )

                estado_j = 'PENDIENTE'
                if juicio_txt:
                    j = juicio_txt.lower()
                    if 'no aprob' in j or 'reprobado' in j:
                        estado_j = 'NO_APROBADO'
                    elif 'aprob' in j:
                        estado_j = 'APROBADO'

                AprendizResultado.objects.update_or_create(
                    aprendiz=aprendiz,
                    resultado=ra_obj,
                    defaults={'estado': estado_j, 'fecha': date.today()}
                )

        except Exception as e:
            print(f"Error en after_import_row: {e}")