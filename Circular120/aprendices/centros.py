# Después de agregar los modelos, ejecutar:
# python manage.py makemigrations
# python manage.py migrate

# Script para poblar los centros de formación de Boyacá
# python manage.py shell

from aprendices.models import CentroFormacion

centros_boyaca = [
    {
        'codigo': '9111',
        'nombre': 'Centro Minero',
        'municipio': 'Sogamoso',
        'direccion': 'Km 5 vía Paipa',
        'telefono': '(8) 7702914',
        'email': 'centrominero@sena.edu.co'
    },
    {
        'codigo': '9112',
        'nombre': 'Centro de Desarrollo Agroempresarial',
        'municipio': 'Chiquinquirá',
        'direccion': 'Carrera 10 No. 18-55',
        'telefono': '(8) 7263080',
        'email': 'cdagrochiquinquira@sena.edu.co'
    },
    {
        'codigo': '9113',
        'nombre': 'Centro de Desarrollo Agroindustrial y Empresarial',
        'municipio': 'Chía',
        'direccion': 'Autopista Norte Km 21',
        'telefono': '(1) 8620707',
        'email': 'cdagrochia@sena.edu.co'
    },
    {
        'codigo': '9114',
        'nombre': 'Centro de Gestión Administrativa y Fortalecimiento Empresarial',
        'municipio': 'Tunja',
        'direccion': 'Calle 11 No. 10-49',
        'telefono': '(8) 7405150',
        'email': 'cgaftunja@sena.edu.co'
    },
    {
        'codigo': '9115',
        'nombre': 'Centro de Desarrollo Tecnológico Agroindustrial',
        'municipio': 'Duitama',
        'direccion': 'Carrera 19 No. 20-55',
        'telefono': '(8) 7606200',
        'email': 'cdtaduitama@sena.edu.co'
    },
]

for centro_data in centros_boyaca:
    CentroFormacion.objects.get_or_create(
        codigo=centro_data['codigo'],
        defaults=centro_data
    )

print("✅ Centros de formación de Boyacá creados")