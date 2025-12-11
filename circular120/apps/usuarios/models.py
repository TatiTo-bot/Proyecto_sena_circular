from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class PerfilUsuario(models.Model):
    """
    Perfil extendido para usuarios del sistema
    """
    ROLES = [
        ('ADMINISTRADOR', 'Administrador'),
        ('COORDINADOR', 'Coordinador Académico'),
        ('INSTRUCTOR', 'Instructor'),
        ('CONSULTA', 'Solo Consulta'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROLES, default='INSTRUCTOR')
    documento = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    centro_formacion = models.CharField(max_length=200, blank=True)
    
    # Preferencias de notificaciones
    recibir_alertas_email = models.BooleanField(default=True)
    recibir_recordatorios = models.BooleanField(default=True)
    frecuencia_recordatorios = models.CharField(
        max_length=20,
        choices=[
            ('DIARIO', 'Diario'),
            ('SEMANAL', 'Semanal'),
            ('QUINCENAL', 'Quincenal'),
        ],
        default='SEMANAL'
    )
    
    # Fechas
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'perfiles_usuario'
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_rol_display()}"
    
    def es_administrador(self):
        return self.rol == 'ADMINISTRADOR'
    
    def es_instructor(self):
        return self.rol == 'INSTRUCTOR'
    
    def es_coordinador(self):
        return self.rol == 'COORDINADOR'
    
    def puede_editar_aprendices(self):
        return self.rol in ['ADMINISTRADOR', 'INSTRUCTOR', 'COORDINADOR']
    
    def puede_importar_archivos(self):
        return self.rol in ['ADMINISTRADOR', 'INSTRUCTOR']


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """Crear perfil automáticamente cuando se crea un usuario"""
    if created:
        PerfilUsuario.objects.create(user=instance)


@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    """Guardar perfil cuando se guarda el usuario"""
    if hasattr(instance, 'perfil'):
        instance.perfil.save()


class HistorialAcceso(models.Model):
    """
    Registro de accesos al sistema para auditoría
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historial_accesos')
    fecha_hora = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    accion = models.CharField(
        max_length=50,
        choices=[
            ('LOGIN', 'Inicio de Sesión'),
            ('LOGOUT', 'Cierre de Sesión'),
            ('PASSWORD_CHANGE', 'Cambio de Contraseña'),
            ('FAILED_LOGIN', 'Intento de Login Fallido'),
        ]
    )
    
    class Meta:
        db_table = 'historial_accesos'
        verbose_name = 'Historial de Acceso'
        verbose_name_plural = 'Historial de Accesos'
        ordering = ['-fecha_hora']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.accion} - {self.fecha_hora}"