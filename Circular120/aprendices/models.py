from django.db import models
from django.utils import timezone

class Ficha(models.Model):
    numero = models.CharField(max_length=50, primary_key=True)
    programa = models.CharField(max_length=200, blank=True)
    instructor = models.CharField(max_length=200, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.numero} - {self.programa or 'Sin programa'}"

class Aprendiz(models.Model):
    documento = models.CharField(max_length=30, primary_key=True)
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    estado_formacion = models.CharField(
        max_length=30,
        choices=[
            ('INDUCCION','INDUCCIÓN'),
            ('FORMACION','FORMACIÓN'),
            ('POR_CERTIFICAR','POR CERTIFICAR'),
            ('CERTIFICADO','CERTIFICADO'),
            ('APLAZADO','APLAZADO'),
            ('REINGRESADO','REINGRESADO'),
            ('DESERTO','DESERTO'),
        ],
        default='FORMACION'
    )
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_final = models.DateField(null=True, blank=True)
    ficha = models.ForeignKey(Ficha, on_delete=models.SET_NULL, null=True, blank=True, related_name='aprendices')
    observaciones = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.documento} - {self.nombre} {self.apellido}"

class Inasistencia(models.Model):
    aprendiz = models.ForeignKey(Aprendiz, on_delete=models.CASCADE, related_name='inasistencias')
    ficha = models.ForeignKey(Ficha, on_delete=models.CASCADE, related_name='inasistencias')
    fecha = models.DateField()
    justificada = models.BooleanField(default=False)
    motivo = models.TextField(blank=True, null=True)
    reportado_por = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Inasistencia {self.aprendiz.documento} {self.fecha}"

class Competencia(models.Model):
    codigo = models.CharField(max_length=50, primary_key=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    duracion_horas = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class ResultadoAprendizaje(models.Model):
    codigo = models.CharField(max_length=50, primary_key=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    competencia = models.ForeignKey(Competencia, on_delete=models.CASCADE, related_name='resultados')

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class AprendizResultado(models.Model):
    aprendiz = models.ForeignKey(Aprendiz, on_delete=models.CASCADE, related_name='resultados_aprendiz')
    resultado = models.ForeignKey(ResultadoAprendizaje, on_delete=models.CASCADE, related_name='aprendices_resultado')
    estado = models.CharField(max_length=30, choices=[('APROBADO','APROBADO'),('NO_APROBADO','NO APROBADO'),('PENDIENTE','PENDIENTE')], default='PENDIENTE')
    fecha = models.DateField(null=True, blank=True)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('aprendiz','resultado')

    def __str__(self):
        return f"{self.aprendiz.documento} - {self.resultado.codigo} - {self.estado}"

class ActaComite(models.Model):
    ficha = models.ForeignKey(Ficha, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateField(default=timezone.now)
    contenido = models.TextField()
    archivo_pdf = models.FileField(upload_to='actas/', null=True, blank=True)
    creado_por = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Acta {self.id} - {self.ficha}"