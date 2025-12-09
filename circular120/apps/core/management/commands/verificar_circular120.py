from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from apps.aprendices.models import Aprendiz
from apps.fichas.models import Ficha


class Command(BaseCommand):
    help = 'Verifica el estado de aprendices según Circular 120'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Verificando Circular 120...'))
        
        # CASO 1: Riesgo de deserción
        dias_limite = settings.CIRCULAR_120['DIAS_DEFINIR_MODALIDAD_PRODUCTIVA']
        fecha_limite = timezone.now().date() - timedelta(days=dias_limite)
        
        aprendices_riesgo = Aprendiz.objects.filter(
            estado_formacion__in=['EN_FORMACION', 'CONDICIONADO'],
            ficha__fecha_fin_lectiva__lt=fecha_limite,
            activo=True
        ).count()
        
        self.stdout.write(f'\n⚠️  CASO 1: Aprendices en riesgo de deserción: {aprendices_riesgo}')
        
        # CASO 3: Por certificar vencidos
        meses_max = settings.CIRCULAR_120['MESES_MAXIMOS_POR_CERTIFICAR']
        fecha_cert_limite = timezone.now().date() - timedelta(days=meses_max * 30)
        
        aprendices_cert = Aprendiz.objects.filter(
            estado_formacion='POR_CERTIFICAR',
            fecha_actualizacion__lt=fecha_cert_limite,
            activo=True
        ).count()
        
        self.stdout.write(f'⚠️  CASO 3: Aprendices Por Certificar vencidos: {aprendices_cert}')
        
        # Fichas vencidas
        fichas_vencidas = Ficha.objects.filter(estado='ACTIVA').filter(
            fecha_fin_lectiva__lt=fecha_limite
        ).count()
        
        self.stdout.write(f'⚠️  Fichas con vigencia vencida: {fichas_vencidas}\n')
        
        if aprendices_riesgo > 0 or aprendices_cert > 0 or fichas_vencidas > 0:
            self.stdout.write(self.style.WARNING('Se encontraron casos pendientes. Revisar dashboard.'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ No hay casos críticos pendientes.'))