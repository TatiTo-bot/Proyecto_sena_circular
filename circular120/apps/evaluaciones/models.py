from django.db import models

class JuicioEvaluativo(models.Model):
    JUICIOS = [
        ('APROBADO', 'Aprobado'),
        ('NO_APROBADO', 'No Aprobado'),
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
    ]
    
    aprendiz = models.ForeignKey(
        'aprendices.Aprendiz',
        on_delete=models.CASCADE,
        related_name='juicios_evaluativos'
    )
    resultado_aprendizaje = models.ForeignKey(
        'competencias.ResultadoAprendizaje',
        on_delete=models.CASCADE
    )
    juicio = models.CharField(max_length=20, choices=JUICIOS)
    fecha_evaluacion = models.DateField()
    observaciones = models.TextField(blank=True, null=True)
    importado_desde_excel = models.BooleanField(default=False)
    archivo_origen = models.ForeignKey(
        'importador.ArchivoImportado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'juicios_evaluativos'
        verbose_name = 'Juicio Evaluativo'
        verbose_name_plural = 'Juicios Evaluativos'
        unique_together = ['aprendiz', 'resultado_aprendizaje', 'fecha_evaluacion']
        indexes = [
            models.Index(fields=['aprendiz', 'juicio']),
        ]
    
    def __str__(self):
        return f"{self.aprendiz} - {self.resultado_aprendizaje.codigo} - {self.juicio}"