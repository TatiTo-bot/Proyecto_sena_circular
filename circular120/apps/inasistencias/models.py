from django.db import models

class Inasistencia(models.Model):
    aprendiz = models.ForeignKey(
        'aprendices.Aprendiz', 
        on_delete=models.CASCADE, 
        related_name='inasistencias'
    )
    fecha = models.DateField(db_index=True)
    justificada = models.BooleanField(default=False)
    motivo = models.TextField(blank=True, null=True)
    soporte_adjunto = models.FileField(
        upload_to='inasistencias/soportes/', 
        null=True, 
        blank=True
    )
    cant_horas = models.FloatField(null=True, blank=True)   # nuevo campo
    instructor = models.CharField(max_length=200, blank=True, null=True)  # nuevo campo
    importado_desde_excel = models.BooleanField(default=False)
    archivo_origen = models.ForeignKey(
        'importador.ArchivoImportado', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inasistencias'
        verbose_name = 'Inasistencia'
        verbose_name_plural = 'Inasistencias'
        unique_together = ['aprendiz', 'fecha']
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['aprendiz', 'fecha']),
            models.Index(fields=['justificada']),
        ]
    
    def __str__(self):
        return f"{self.aprendiz} - {self.fecha}"