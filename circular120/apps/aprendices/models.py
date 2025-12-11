from django.db import models
from django.core.validators import EmailValidator

class Aprendiz(models.Model):
    ESTADOS_FORMACION = [
        ('EN_FORMACION', 'En Formación'),
        ('POR_CERTIFICAR', 'Por Certificar'),
        ('CERTIFICADO', 'Certificado'),
        ('RETIRO_VOLUNTARIO', 'Retiro Voluntario'),
        ('CANCELADO', 'Cancelado'),
        ('CONDICIONADO', 'Condicionado'),
        ('VIGENCIA_VENCIDA', 'Vigencia Vencida'),
    ]
    
    documento = models.CharField(max_length=20, unique=True, db_index=True)
    tipo_documento = models.CharField(max_length=5, choices=[
        ('CC', 'Cédula de Ciudadanía'),
        ('TI', 'Tarjeta de Identidad'),
        ('CE', 'Cédula de Extranjería'),
        ('PEP', 'Permiso Especial de Permanencia'),
    ], default='CC')

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField(validators=[EmailValidator()])
    telefono = models.CharField(max_length=20, blank=True, null=True)

    estado_formacion = models.CharField(
        max_length=30,
        choices=ESTADOS_FORMACION,
        default='EN_FORMACION'
    )

    ficha = models.ForeignKey(
        'fichas.Ficha',
        on_delete=models.PROTECT,
        related_name='aprendices'
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'aprendices'
        verbose_name = 'Aprendiz'
        verbose_name_plural = 'Aprendices'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f"{self.documento} - {self.nombre} {self.apellido}"

    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    def porcentaje_asistencia(self):
        """Calcula el porcentaje de asistencia del aprendiz"""
        from apps.inasistencias.models import Inasistencia
        from django.utils import timezone
        from datetime import timedelta
        
        # Contar días hábiles desde inicio de ficha hasta hoy
        inicio = self.ficha.fecha_inicio
        hoy = timezone.now().date()
        
        if hoy < inicio:
            return 100.0
        
        # Días totales (aproximado, sin contar festivos)
        dias_totales = (hoy - inicio).days
        dias_habiles = dias_totales * 5 / 7  # Aproximación de días hábiles
        
        if dias_habiles == 0:
            return 100.0
        
        # Contar inasistencias
        inasistencias = Inasistencia.objects.filter(
            aprendiz=self,
            fecha__gte=inicio,
            fecha__lte=hoy
        ).count()
        
        # Calcular porcentaje
        porcentaje = ((dias_habiles - inasistencias) / dias_habiles) * 100
        return max(0, min(100, porcentaje))  # Entre 0 y 100
    
    def tiene_inasistencias_criticas(self):
        """Verifica si el aprendiz tiene un porcentaje crítico de inasistencias"""
        from django.conf import settings
        return self.porcentaje_asistencia() < settings.CIRCULAR_120['PORCENTAJE_MINIMO_ASISTENCIA']
    
    def dias_desde_fin_lectiva(self):
        """Calcula los días transcurridos desde el fin de la etapa lectiva"""
        from django.utils import timezone
        
        if not self.ficha.fecha_fin_lectiva:
            return 0
        
        if timezone.now().date() < self.ficha.fecha_fin_lectiva:
            return 0
        
        return (timezone.now().date() - self.ficha.fecha_fin_lectiva).days
    
    def esta_en_riesgo_desercion(self):
        """Verifica si el aprendiz está en riesgo de deserción según Circular 120"""
        from django.conf import settings
        
        dias_limite = settings.CIRCULAR_120['DIAS_DEFINIR_MODALIDAD_PRODUCTIVA']
        dias_transcurridos = self.dias_desde_fin_lectiva()
        
        return (
            self.estado_formacion in ['EN_FORMACION', 'CONDICIONADO'] and
            dias_transcurridos > dias_limite
        )