# aprendices/models.py
from django.db import models
from django.contrib.auth.models import User
from datetime import date, timedelta

class CentroFormacion(models.Model):
    """Centros de formación de la Regional Boyacá"""
    codigo = models.CharField(max_length=10, unique=True, verbose_name='Código del Centro')
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Centro')
    municipio = models.CharField(max_length=100, verbose_name='Municipio')
    direccion = models.TextField(blank=True, null=True, verbose_name='Dirección')
    telefono = models.CharField(max_length=50, blank=True, null=True, verbose_name='Teléfono')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    activo = models.BooleanField(default=True, verbose_name='¿Activo?')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Centro de Formación'
        verbose_name_plural = 'Centros de Formación'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Ficha(models.Model):
    numero = models.CharField(max_length=10, primary_key=True, verbose_name='Número de Ficha')
    programa = models.CharField(max_length=200, verbose_name='Programa de Formación', default='Por definir')
    instructor = models.CharField(max_length=100, blank=True, null=True, verbose_name='Instructor Principal')
    fecha_inicio = models.DateField(blank=True, null=True, verbose_name='Fecha de Inicio')
    fecha_fin = models.DateField(blank=True, null=True, verbose_name='Fecha de Finalización')
    centro = models.ForeignKey(
        CentroFormacion, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='fichas',
        verbose_name='Centro de Formación'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ficha de Caracterización'
        verbose_name_plural = 'Fichas de Caracterización'
        ordering = ['-numero']
    
    def __str__(self):
        return f"{self.numero} - {self.programa}"


class Aprendiz(models.Model):
    ESTADO_FORMACION_CHOICES = [
        ('EN_FORMACION', 'En Formación'),
        ('ETAPA_LECTIVA', 'Etapa Lectiva'),
        ('ETAPA_PRODUCTIVA', 'Etapa Productiva'),
        ('POR_CERTIFICAR', 'Por Certificar'),
        ('CERTIFICADO', 'Certificado'),
        ('CANCELADO', 'Cancelado'),
        ('RETIRO_VOLUNTARIO', 'Retiro Voluntario'),
        ('APLAZAMIENTO', 'Aplazamiento'),
        ('TRASLADADO', 'Trasladado'),
    ]
    
    documento = models.CharField(max_length=20, primary_key=True, verbose_name='Documento de Identidad')
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    apellido = models.CharField(max_length=100, verbose_name='Apellido')
    email = models.EmailField(blank=True, null=True, verbose_name='Correo Electrónico')
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name='Teléfono')
    
    estado_formacion = models.CharField(
        max_length=30,
        choices=ESTADO_FORMACION_CHOICES,
        default='EN_FORMACION',
        verbose_name='Estado de Formación'
    )
    
    fecha_inicio = models.DateField(blank=True, null=True, verbose_name='Fecha de Inicio')
    fecha_final = models.DateField(blank=True, null=True, verbose_name='Fecha Final')
    fecha_fin_lectiva = models.DateField(blank=True, null=True, verbose_name='Fecha Fin Etapa Lectiva')
    fecha_fin_productiva = models.DateField(blank=True, null=True, verbose_name='Fecha Fin Etapa Productiva')
    
    ficha = models.ForeignKey(
        Ficha,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='aprendices',
        verbose_name='Ficha de Caracterización'
    )
    
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Aprendiz'
        verbose_name_plural = 'Aprendices'
        ordering = ['apellido', 'nombre']
    
    def __str__(self):
        return f"{self.documento} - {self.nombre} {self.apellido}"
    
    def dias_vencido(self):
        """Calcula cuántos días lleva vencido"""
        hoy = date.today()
        if self.fecha_fin_productiva and self.fecha_fin_productiva < hoy:
            return (hoy - self.fecha_fin_productiva).days
        if self.ficha and self.ficha.fecha_fin and self.ficha.fecha_fin < hoy:
            return (hoy - self.ficha.fecha_fin).days
        return 0


class Inasistencia(models.Model):
    aprendiz = models.ForeignKey(
        Aprendiz,
        on_delete=models.CASCADE,
        related_name='inasistencias',
        verbose_name='Aprendiz'
    )
    ficha = models.ForeignKey(
        Ficha,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Ficha'
    )
    fecha = models.DateField(verbose_name='Fecha de Inasistencia')
    justificada = models.BooleanField(default=False, verbose_name='¿Justificada?')
    motivo = models.TextField(blank=True, null=True, verbose_name='Motivo')
    reportado_por = models.CharField(max_length=100, blank=True, null=True, verbose_name='Reportado Por')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Inasistencia'
        verbose_name_plural = 'Inasistencias'
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.aprendiz} - {self.fecha}"


class Competencia(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name='Código de Competencia')
    nombre = models.CharField(max_length=500, verbose_name='Nombre de la Competencia')
    
    class Meta:
        verbose_name = 'Competencia'
        verbose_name_plural = 'Competencias'
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ResultadoAprendizaje(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name='Código del Resultado')
    nombre = models.CharField(max_length=500, verbose_name='Descripción del Resultado')
    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.CASCADE,
        related_name='resultados',
        null=True,
        blank=True,
        verbose_name='Competencia'
    )
    
    class Meta:
        verbose_name = 'Resultado de Aprendizaje'
        verbose_name_plural = 'Resultados de Aprendizaje'
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class AprendizResultado(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('NO_APROBADO', 'No Aprobado'),
    ]
    
    aprendiz = models.ForeignKey(
        Aprendiz,
        on_delete=models.CASCADE,
        related_name='juicios',
        verbose_name='Aprendiz'
    )
    resultado = models.ForeignKey(
        ResultadoAprendizaje,
        on_delete=models.CASCADE,
        verbose_name='Resultado de Aprendizaje'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado'
    )
    fecha = models.DateField(verbose_name='Fecha de Evaluación')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Juicio Evaluativo'
        verbose_name_plural = 'Juicios Evaluativos'
        unique_together = [['aprendiz', 'resultado']]
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.aprendiz} - {self.resultado.codigo} ({self.estado})"


class ActaComite(models.Model):
    ficha = models.ForeignKey(
        Ficha,
        on_delete=models.CASCADE,
        related_name='actas',
        verbose_name='Ficha'
    )
    fecha = models.DateField(verbose_name='Fecha del Comité')
    contenido = models.TextField(verbose_name='Contenido del Acta')
    archivo_pdf = models.FileField(
        upload_to='actas/',
        blank=True,
        null=True,
        verbose_name='Archivo PDF'
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Creado Por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Acta de Comité'
        verbose_name_plural = 'Actas de Comité'
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Acta {self.ficha} - {self.fecha}"


class RolAdministrativo(models.Model):
    """Subdirectores y Coordinadores del Centro"""
    TIPO_ROL_CHOICES = [
        ('SUBDIRECTOR', 'Subdirector'),
        ('COORDINADOR_ACADEMICO', 'Coordinador Académico'),
        ('COORDINADOR_FORMACION', 'Coordinador de Formación'),
        ('COORDINADOR_MISIONAL', 'Coordinador Misional'),
        ('COORDINADOR_ADMINISTRATIVO', 'Coordinador Administrativo'),
    ]
    
    usuario = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        verbose_name='Usuario',
        help_text='Usuario asociado a este rol'
    )
    tipo_rol = models.CharField(
        max_length=50, 
        choices=TIPO_ROL_CHOICES, 
        verbose_name='Tipo de Rol'
    )
    centro = models.ForeignKey(
        CentroFormacion, 
        on_delete=models.CASCADE, 
        related_name='roles',
        verbose_name='Centro de Formación'
    )
    
    fecha_inicio = models.DateField(verbose_name='Fecha de Inicio del Rol')
    fecha_fin = models.DateField(blank=True, null=True, verbose_name='Fecha de Fin del Rol')
    
    activo = models.BooleanField(default=True, verbose_name='¿Activo?')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Rol Administrativo'
        verbose_name_plural = 'Roles Administrativos'
        ordering = ['-activo', 'centro', 'tipo_rol']
        unique_together = [['usuario', 'tipo_rol', 'centro', 'activo']]
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.get_tipo_rol_display()} ({self.centro.nombre})"
    
    def deshabilitar(self):
        """Deshabilita el rol sin eliminarlo"""
        self.activo = False
        self.fecha_fin = date.today()
        self.save()