from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

class Programa(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    nivel = models.CharField(max_length=50, choices=[
        ('TECNICO', 'Técnico'),
        ('TECNOLOGO', 'Tecnólogo'),
        ('ESPECIALIZACION', 'Especialización Tecnológica'),
        ('OPERARIO', 'Operario'),
    ])
    duracion_meses = models.IntegerField(help_text="Duración total en meses")
    activo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'programas'
        verbose_name = 'Programa'
        verbose_name_plural = 'Programas'
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Ficha(models.Model):
    ESTADOS = [
        ('ACTIVA', 'Activa'),
        ('FINALIZADA', 'Finalizada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    numero = models.CharField(max_length=20, unique=True, db_index=True)
    programa = models.ForeignKey(Programa, on_delete=models.PROTECT)
    fecha_inicio = models.DateField()
    fecha_fin_lectiva = models.DateField()
    fecha_fin_practica = models.DateField(null=True, blank=True)
    instructor_lider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='fichas_lideradas'
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVA')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fichas'
        verbose_name = 'Ficha'
        verbose_name_plural = 'Fichas'
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['estado', 'fecha_fin_lectiva']),
        ]
    
    def __str__(self):
        return f"Ficha {self.numero} - {self.programa.nombre}"
    
    def dias_transcurridos(self):
        if timezone.now().date() < self.fecha_inicio:
            return 0
        return (timezone.now().date() - self.fecha_inicio).days
    
    def esta_vencida(self):
        if not self.fecha_fin_practica:
            fecha_limite = self.fecha_fin_lectiva
        else:
            fecha_limite = self.fecha_fin_practica
        
        dias_max = settings.CIRCULAR_120['DIAS_MAXIMOS_CERTIFICACION']
        fecha_vencimiento = fecha_limite + timedelta(days=dias_max)
        return timezone.now().date() > fecha_vencimiento
    
    def dias_para_vencimiento_certificacion(self):
        """
        Calcula días para vencimiento según Circular 120:
        - 18 meses después de finalizada etapa lectiva para definir modalidad productiva
        """
        fecha_limite = self.fecha_fin_lectiva
        dias_max = settings.CIRCULAR_120['DIAS_DEFINIR_MODALIDAD_PRODUCTIVA']
        fecha_vencimiento = fecha_limite + timedelta(days=dias_max)
        dias_restantes = (fecha_vencimiento - timezone.now().date()).days
        return dias_restantes
    
    def esta_en_periodo_critico(self):
        """
        Verifica si está en periodo crítico (menos de 90 días para vencimiento)
        """
        dias_restantes = self.dias_para_vencimiento_certificacion()
        return dias_restantes is not None and 0 < dias_restantes <= 90
