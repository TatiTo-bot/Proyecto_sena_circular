from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.fichas.models import Programa, Ficha
from apps.aprendices.models import Aprendiz
from apps.competencias.models import Competencia, ResultadoAprendizaje
from datetime import date, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Carga datos de demostración para probar el sistema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Cargando datos de demostración...'))
        
        # Crear instructor de prueba
        instructor, created = User.objects.get_or_create(
            username='instructor_demo',
            defaults={
                'email': 'instructor@sena.edu.co',
                'first_name': 'Juan',
                'last_name': 'Instructor',
                'is_staff': False,
            }
        )
        if created:
            instructor.set_password('instructor123')
            instructor.save()
            self.stdout.write(self.style.SUCCESS('  ✅ Instructor demo creado'))
        
        # Crear programa
        programa, created = Programa.objects.get_or_create(
            codigo='228106',
            defaults={
                'nombre': 'Tecnología en Análisis y Desarrollo de Software',
                'nivel': 'TECNOLOGO',
                'duracion_meses': 24,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Programa {programa.codigo} creado'))
        
        # Crear competencias
        competencia1, created = Competencia.objects.get_or_create(
            codigo='220501046',
            defaults={
                'nombre': 'Desarrollar el sistema que cumpla con los requisitos de la solución informática',
                'programa': programa,
                'duracion_horas': 400,
            }
        )
        
        # Crear RAs
        ra1, created = ResultadoAprendizaje.objects.get_or_create(
            codigo='22050104601',
            defaults={
                'descripcion': 'Construir el sistema que cumpla con los requisitos de la solución informática',
                'competencia': competencia1,
            }
        )
        
        # Crear fichas
        ficha1, created = Ficha.objects.get_or_create(
            numero='2819058',
            defaults={
                'programa': programa,
                'fecha_inicio': date.today() - timedelta(days=365),
                'fecha_fin_lectiva': date.today() + timedelta(days=365),
                'fecha_fin_practica': date.today() + timedelta(days=545),
                'instructor_lider': instructor,
                'estado': 'ACTIVA',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Ficha {ficha1.numero} creada'))
        
        # Crear aprendices de prueba
        aprendices_data = [
            ('1234567890', 'Carlos', 'Rodríguez', 'carlos.rodriguez@sena.edu.co'),
            ('0987654321', 'María', 'González', 'maria.gonzalez@sena.edu.co'),
            ('1122334455', 'Pedro', 'Martínez', 'pedro.martinez@sena.edu.co'),
            ('5544332211', 'Ana', 'López', 'ana.lopez@sena.edu.co'),
        ]
        
        for doc, nombre, apellido, email in aprendices_data:
            aprendiz, created = Aprendiz.objects.get_or_create(
                documento=doc,
                defaults={
                    'tipo_documento': 'CC',
                    'nombre': nombre,
                    'apellido': apellido,
                    'email': email,
                    'estado_formacion': 'EN_FORMACION',
                    'ficha': ficha1,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Aprendiz {nombre} {apellido} creado'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Datos de demostración cargados exitosamente'))
        self.stdout.write(self.style.WARNING('\n📝 Credenciales del instructor:'))
        self.stdout.write(self.style.WARNING('   Usuario: instructor_demo'))
        self.stdout.write(self.style.WARNING('   Contraseña: instructor123'))
