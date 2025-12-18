#!/usr/bin/env python
"""
Script para probar el parseo de tu Excel específico
Guarda este archivo como: test_excel.py
Ejecuta: python test_excel.py ruta/a/tu/archivo.xlsx
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'circular120.settings')
django.setup()

from apps.importador.excel_parser import ExcelParser
import pandas as pd

def test_excel(ruta_archivo):
    """Prueba el parseo del Excel"""
    
    print("\n" + "="*80)
    print("🔍 PRUEBA DE PARSEO DE EXCEL SENA")
    print("="*80 + "\n")
    
    print(f"📂 Archivo: {ruta_archivo}\n")
    
    # 1. Leer con pandas directamente
    print("📊 PASO 1: Lectura directa con pandas")
    print("-" * 80)
    
    try:
        df = pd.read_excel(ruta_archivo, engine='openpyxl')
        print(f"✅ Archivo leído correctamente")
        print(f"   Filas: {len(df)}")
        print(f"   Columnas: {len(df.columns)}\n")
        
        print("📋 Columnas originales:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i}. '{col}'")
        
        print("\n👁️  Primeras 2 filas:")
        print(df.head(2).to_string())
        print()
        
    except Exception as e:
        print(f"❌ Error leyendo con pandas: {e}")
        return
    
    # 2. Probar con el parser
    print("\n🤖 PASO 2: Prueba con ExcelParser")
    print("-" * 80)
    
    try:
        parser = ExcelParser(ruta_archivo)
        
        if not parser.load_file():
            print("❌ El parser no pudo cargar el archivo")
            return
        
        print("✅ Parser cargó el archivo correctamente\n")
        
        print("🔄 Columnas normalizadas por el parser:")
        for col in parser.df.columns:
            original = df.columns[list(parser.df.columns).index(col)]
            print(f"   '{original}' -> '{col}'")
        
        print("\n🔍 PASO 3: Intentando parsear inasistencias")
        print("-" * 80)
        
        registros, errores = parser.parse_inasistencias()
        
        if errores:
            print(f"\n⚠️  ERRORES ENCONTRADOS ({len(errores)}):")
            for error in errores[:5]:
                print(f"   • {error}")
        
        if registros:
            print(f"\n✅ REGISTROS PARSEADOS: {len(registros)}\n")
            
            print("📝 Primeros 3 registros:")
            for i, reg in enumerate(registros[:3], 1):
                print(f"\n   Registro {i} (Fila Excel {reg['fila_excel']}):")
                print(f"      Documento: {reg['tipo_documento']} - {reg['documento']}")
                print(f"      Nombre: {reg['nombre']} {reg['apellido']}")
                print(f"      Ficha: {reg['numero_ficha']}")
                print(f"      Programa: {reg['programa_nombre']}")
                print(f"      Fecha: {reg['fecha']}")
                print(f"      Horas: {reg['cant_horas']}")
                print(f"      Justificada: {'✅ Sí' if reg['justificada'] else '❌ No'}")
        else:
            print("\n❌ NO SE PARSEARON REGISTROS")
        
        # 4. Análisis de columnas
        print("\n\n🔍 PASO 4: Análisis detallado de columnas")
        print("-" * 80)
        
        columnas_buscadas = {
            'FICHA': ['FICHA', 'NUMERO FICHA'],
            'DOCUMENTO': ['IDENTIFICACION APRENDIZ', 'IDENTIFICACIÓN APRENDIZ', 'DOCUMENTO'],
            'APRENDIZ': ['APRENDIZ', 'NOMBRE'],
            'FECHA': ['FECHA INICIO', 'FECHA'],
            'HORAS': ['CANT. HORAS', 'CANT HORAS'],
            'JUSTIFICACION': ['JUSTIFICACION', 'JUSTIFICACIÓN']
        }
        
        for tipo, variantes in columnas_buscadas.items():
            col_encontrada = parser._find_column(variantes)
            if col_encontrada:
                print(f"   ✅ {tipo}: '{col_encontrada}'")
            else:
                print(f"   ❌ {tipo}: NO ENCONTRADA")
                print(f"      Buscando: {', '.join(variantes)}")
        
        print("\n" + "="*80)
        print("✅ ANÁLISIS COMPLETADO")
        print("="*80 + "\n")
        
        if registros and len(registros) > 0:
            print("🎉 ¡EL ARCHIVO SE PUEDE IMPORTAR CORRECTAMENTE!")
            print(f"   Se procesarían {len(registros)} registros")
        else:
            print("⚠️  EL ARCHIVO TIENE PROBLEMAS")
            print("   Revisa los errores arriba para más detalles")
        
    except Exception as e:
        print(f"\n❌ ERROR EN EL PARSER: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❌ Uso: python test_excel.py ruta/al/archivo.xlsx\n")
        sys.exit(1)
    
    archivo = sys.argv[1]
    
    if not os.path.exists(archivo):
        print(f"\n❌ El archivo no existe: {archivo}\n")
        sys.exit(1)
    
    test_excel(archivo)