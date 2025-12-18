# test_import.py - Script para probar importación
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'circular120.settings')
django.setup()

from apps.importador.excel_parser import ExcelParser

# Prueba el parser
archivo = 'ruta/al/archivo.xlsx'
parser = ExcelParser(archivo)

if parser.load_file():
    print(f"✅ Archivo cargado correctamente")
    print(f"📊 Ficha detectada: {parser.ficha_numero}")
    
    registros, errores = parser.parse_inasistencias()
    print(f"📝 Registros encontrados: {len(registros)}")
    print(f"❌ Errores: {len(errores)}")
    
    if registros:
        print("\nPrimer registro:")
        print(registros[0])
    
    if errores:
        print("\nErrores:")
        for error in errores[:5]:
            print(f"  - {error}")
else:
    print("❌ No se pudo cargar el archivo")