from django.db import models

class Competencia(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=300)
    programa = models.ForeignKey(
        'fichas.Programa',
        on_delete=models.CASCADE,
        related_name='competencias'
    )
    duracion_horas = models.IntegerField()
    
    class Meta:
        db_table = 'competencias'
        verbose_name = 'Competencia'
        verbose_name_plural = 'Competencias'
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class ResultadoAprendizaje(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField()
    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.CASCADE,
        related_name='resultados_aprendizaje'
    )
    
    class Meta:
        db_table = 'resultados_aprendizaje'
        verbose_name = 'Resultado de Aprendizaje'
        verbose_name_plural = 'Resultados de Aprendizaje'
    
    def __str__(self):
        return f"{self.codigo}"
    