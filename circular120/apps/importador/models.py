from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ArchivoImportado(models.Model):
    TIPOS = [
        ('INASISTENCIAS', 'Inasistencias'),
        ('EVALUACIONES', 'Juicios Evaluativos'),
    ]
    
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('PROCESANDO', 'Procesando'),
        ('COMPLETADO', 'Completado'),
        ('ERROR', 'Error'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPOS)
    archivo = models.FileField(upload_to='imports/%Y/%m/')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    ficha = models.ForeignKey('fichas.Ficha', on_delete=models.CASCADE, null=True)
    fecha_importacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    registros_importados = models.IntegerField(default=0)
    registros_error = models.IntegerField(default=0)
    registros_omitidos = models.IntegerField(default=0)
    log_errores = models.TextField(blank=True, null=True)
    tiempo_proceso = models.FloatField(null=True, help_text="Segundos")
    
    class Meta:
        db_table = 'archivos_importados'
        verbose_name = 'Archivo Importado'
        verbose_name_plural = 'Archivos Importados'
        ordering = ['-fecha_importacion']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.fecha_importacion}"
    
    class Justificada(models.Model):
    aprendiz = models.ForeignKey('aprendices.Aprendiz', on_delete=models.CASCADE, related_name='justificadas')
    fecha = models.DateField(db_index=True)
    instructor = models.CharField(max_length=200, blank=True, null=True)   # viene desde Excel
    ficha_numero = models.CharField(max_length=50, blank=True, null=True)   # número de ficha (solo número)
    horas = models.FloatField(null=True, blank=True)   # cant_horas desde excel
    motivo = models.TextField(blank=True, null=True)
    importado_desde_excel = models.BooleanField(default=True)
    archivo_origen = models.ForeignKey('ArchivoImportado', on_delete=models.SET_NULL, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'justificadas'
        verbose_name = 'Justificada'
        verbose_name_plural = 'Justificadas'
        unique_together = ['aprendiz', 'fecha']

    def __str__(self):
        return f"{self.aprendiz} - {self.fecha}"