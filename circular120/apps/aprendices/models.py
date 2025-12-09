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
