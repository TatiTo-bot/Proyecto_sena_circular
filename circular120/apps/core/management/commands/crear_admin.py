from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from apps.usuarios.models import PerfilUsuario


class Command(BaseCommand):
    help = 'Crea un usuario administrador con todos los permisos'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Nombre de usuario')
        parser.add_argument('--email', type=str, help='Correo electrónico')
        parser.add_argument('--password', type=str, help='Contraseña')

    def handle(self, *args, **kwargs):
        username = kwargs.get('username') or input('Nombre de usuario: ')
        email = kwargs.get('email') or input('Correo electrónico: ')
        password = kwargs.get('password') or input('Contraseña: ')
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'El usuario {username} ya existe'))
            return
        
        # Crear usuario
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name='Admin',
            last_name='Sistema'
        )
        
        # Crear o actualizar perfil
        perfil, created = PerfilUsuario.objects.get_or_create(
            user=user,
            defaults={
                'rol': 'ADMINISTRADOR',
                'documento': '0000000000',
                'centro_formacion': 'Centro de Biotecnología Agropecuaria',
            }
        )
        
        if not created:
            perfil.rol = 'ADMINISTRADOR'
            perfil.save()
        
        # Agregar al grupo Administrador
        grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
        user.groups.add(grupo_admin)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Usuario administrador "{username}" creado exitosamente'))
        self.stdout.write(self.style.SUCCESS(f'   Email: {email}'))
        self.stdout.write(self.style.SUCCESS(f'   Rol: Administrador'))