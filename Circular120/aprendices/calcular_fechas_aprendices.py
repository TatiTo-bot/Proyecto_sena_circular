from django.core.management.base import BaseCommand
from dateutil.relativedelta import relativedelta
from aprendices.models import Aprendiz


class Command(BaseCommand):
    help = 'Calcula fecha_fin_lectiva y fecha_fin_productiva para aprendices existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Sobreescribir fechas aunque ya existan',
        )
        parser.add_argument(
            '--ficha',
            type=str,
            help='Procesar solo aprendices de una ficha específica',
        )

    def handle(self, *args, **options):
        forzar = options['forzar']
        ficha_num = options.get('ficha')

        qs = Aprendiz.objects.select_related('ficha').all()
        if ficha_num:
            qs = qs.filter(ficha__numero=ficha_num)

        total = qs.count()
        actualizados = 0
        sin_fecha = 0

        self.stdout.write(f'\n📋 Procesando {total} aprendices...\n')

        for aprendiz in qs:
            # Determinar la fecha de fin a usar
            fecha_fin = (
                aprendiz.fecha_final
                or (aprendiz.ficha.fecha_fin if aprendiz.ficha else None)
            )
            fecha_inicio = (
                aprendiz.fecha_inicio
                or (aprendiz.ficha.fecha_inicio if aprendiz.ficha else None)
            )

            if not fecha_fin:
                sin_fecha += 1
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ {aprendiz.documento} - Sin fecha de fin')
                )
                continue

            cambios = []

            # fecha_inicio
            if fecha_inicio and (forzar or not aprendiz.fecha_inicio):
                aprendiz.fecha_inicio = fecha_inicio
                cambios.append('fecha_inicio')

            # fecha_final
            if forzar or not aprendiz.fecha_final:
                aprendiz.fecha_final = fecha_fin
                cambios.append('fecha_final')

            # fecha_fin_productiva = fecha_fin
            if forzar or not aprendiz.fecha_fin_productiva:
                aprendiz.fecha_fin_productiva = fecha_fin
                cambios.append('fecha_fin_productiva')

            # fecha_fin_lectiva = fecha_fin - 6 meses
            if forzar or not aprendiz.fecha_fin_lectiva:
                aprendiz.fecha_fin_lectiva = fecha_fin - relativedelta(months=6)
                cambios.append('fecha_fin_lectiva')

            if cambios:
                aprendiz.save(update_fields=cambios)
                actualizados += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✅ {aprendiz.documento} - {aprendiz.nombre} {aprendiz.apellido} '
                        f'→ Lectiva: {aprendiz.fecha_fin_lectiva} | Productiva: {aprendiz.fecha_fin_productiva}'
                    )
                )

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✅ Actualizados: {actualizados}'))
        if sin_fecha:
            self.stdout.write(self.style.WARNING(f'⚠  Sin fecha de fin: {sin_fecha}'))
        self.stdout.write(f'📋 Total procesados: {total}\n')