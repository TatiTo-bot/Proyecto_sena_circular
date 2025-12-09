from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.aprendices.models import Aprendiz
from apps.fichas.models import Ficha, Programa
from apps.competencias.models import Competencia, ResultadoAprendizaje


class Command(BaseCommand):
    help = 'Configuración inicial del sistema: crea grupos y permisos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando configuración...'))
        
        # Crear grupos
        self.crear_grupos()
        
        self.stdout.write(self.style.SUCCESS('✅ Configuración completada'))

    def crear_grupos(self):
        """Crea los grupos de usuarios según requerimientos"""
        
        # 1. Grupo Administrador (Coordinación)
        admin_group, created = Group.objects.get_or_create(name='Administrador')
        if created:
            # Dar todos los permisos
            admin_group.permissions.set(Permission.objects.all())
            self.stdout.write(self.style.SUCCESS('  ✅ Grupo Administrador creado'))
        
        # 2. Grupo Instructor
        instructor_group, created = Group.objects.get_or_create(name='Instructor')
        if created:
            permisos_instructor = [
                # Aprendices - solo ver y editar básico
                'view_aprendiz',
                'change_aprendiz',
                
                # Fichas - solo ver sus fichas
                'view_ficha',
                
                # Inasistencias - agregar y ver
                'add_inasistencia',
                'view_inasistencia',
                
                # Evaluaciones - agregar y ver
                'add_juicioevaluativo',
                'view_juicioevaluativo',
                'change_juicioevaluativo',
                
                # Importador - subir archivos
                'add_archivoimportado',
                'view_archivoimportado',
                
                # Competencias - solo ver
                'view_competencia',
                'view_resultadoaprendizaje',
            ]
            
            permisos = Permission.objects.filter(codename__in=permisos_instructor)
            instructor_group.permissions.set(permisos)
            self.stdout.write(self.style.SUCCESS('  ✅ Grupo Instructor creado'))
        
        # 3. Grupo Consulta
        consulta_group, created = Group.objects.get_or_create(name='Consulta')
        if created:
            permisos_consulta = [
                'view_aprendiz',
                'view_ficha',
                'view_inasistencia',
                'view_juicioevaluativo',
                'view_competencia',
                'view_resultadoaprendizaje',
                'view_archivoimportado',
            ]
            
            permisos = Permission.objects.filter(codename__in=permisos_consulta)
            consulta_group.permissions.set(permisos)
            self.stdout.write(self.style.SUCCESS('  ✅ Grupo Consulta creado'))

