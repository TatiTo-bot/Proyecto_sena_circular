# apps/importador/pdf_to_excel.py
"""
Utilidad para convertir PDFs de inasistencias del SENA a formato Excel
El SENA genera PDFs que necesitan ser convertidos para importación
"""

import pandas as pd
import re
from typing import List, Dict
import logging

logger = logging.getLogger('importador')


def extraer_datos_pdf_inasistencias(texto_pdf: str) -> pd.DataFrame:
    """
    Extrae datos de un PDF de inasistencias del SENA
    
    Formato esperado:
    IDENTIFICACIÓN APRENDIZ | APRENDIZ | FECHA INICIO | FECHA FIN | CANT. HORAS | JUSTIFICACION
    CC - 1057979354         | NOMBRE   | 07/11/2025   | 07/11/2025| 6           | TEXTO
    
    Args:
        texto_pdf: Texto extraído del PDF
        
    Returns:
        DataFrame con columnas: identificacion, aprendiz, fecha_inicio, fecha_fin, justificacion
    """
    
    lineas = texto_pdf.split('\n')
    datos = []
    
    # Patrones para detectar
    patron_identificacion = r'(CC|TI|CE|PPT|PEP)\s*-\s*(\d+)'
    patron_fecha = r'(\d{2}/\d{2}/\d{4})'
    
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        
        # Buscar identificación (CC - 1234567890)
        match_id = re.search(patron_identificacion, linea)
        
        if match_id:
            tipo_doc = match_id.group(1)
            numero_doc = match_id.group(2)
            identificacion = f"{tipo_doc} - {numero_doc}"
            
            # Buscar nombre del aprendiz (puede estar en la misma línea o siguiente)
            nombre = ""
            fecha_inicio = ""
            fecha_fin = ""
            justificacion = ""
            
            # Extraer nombre (después de la identificación)
            resto_linea = linea[match_id.end():].strip()
            if resto_linea:
                # El nombre puede contener fechas después
                partes = resto_linea.split()
                nombre_partes = []
                for parte in partes:
                    if re.match(r'\d{2}/\d{2}/\d{4}', parte):
                        break
                    nombre_partes.append(parte)
                nombre = ' '.join(nombre_partes)
            
            # Buscar fechas en las siguientes líneas
            for j in range(i, min(i + 5, len(lineas))):
                linea_busqueda = lineas[j]
                fechas = re.findall(patron_fecha, linea_busqueda)
                if len(fechas) >= 2:
                    fecha_inicio = fechas[0]
                    fecha_fin = fechas[1]
                    break
                elif len(fechas) == 1 and not fecha_inicio:
                    fecha_inicio = fechas[0]
                    fecha_fin = fechas[0]
            
            # Buscar justificación (líneas siguientes con texto largo)
            for j in range(i + 1, min(i + 10, len(lineas))):
                linea_just = lineas[j].strip()
                if len(linea_just) > 30 and not re.search(patron_identificacion, linea_just):
                    justificacion = linea_just
                    break
            
            if nombre and fecha_inicio:
                datos.append({
                    'IDENTIFICACIÓN APRENDIZ': identificacion,
                    'APRENDIZ': nombre,
                    'FECHA INICIO': fecha_inicio,
                    'FECHA FIN': fecha_fin,
                    'JUSTIFICACION': justificacion
                })
        
        i += 1
    
    df = pd.DataFrame(datos)
    logger.info(f"Extraídos {len(datos)} registros del PDF")
    return df


def convertir_pdf_inasistencias_a_excel(archivo_pdf_path: str, archivo_excel_path: str):
    """
    Convierte un PDF de inasistencias del SENA a Excel
    
    Args:
        archivo_pdf_path: Ruta al archivo PDF
        archivo_excel_path: Ruta donde guardar el Excel
    """
    try:
        # Opción 1: Usar PyPDF2 o pdfplumber
        import pdfplumber
        
        texto_completo = ""
        with pdfplumber.open(archivo_pdf_path) as pdf:
            for page in pdf.pages:
                texto_completo += page.extract_text() + "\n"
        
        # Extraer datos
        df = extraer_datos_pdf_inasistencias(texto_completo)
        
        # Guardar a Excel
        df.to_excel(archivo_excel_path, index=False, engine='openpyxl')
        logger.info(f"PDF convertido exitosamente a {archivo_excel_path}")
        
        return True, f"Convertidos {len(df)} registros"
        
    except Exception as e:
        logger.error(f"Error convirtiendo PDF: {e}")
        return False, str(e)


# Ejemplo de uso en vista
"""
from apps.importador.pdf_to_excel import convertir_pdf_inasistencias_a_excel

# En la vista de importación
if archivo.name.endswith('.pdf'):
    # Convertir PDF a Excel temporalmente
    excel_temp_path = filepath.replace('.pdf', '.xlsx')
    exito, mensaje = convertir_pdf_inasistencias_a_excel(filepath, excel_temp_path)
    
    if exito:
        filepath = excel_temp_path  # Usar el Excel convertido
    else:
        raise Exception(f"Error convirtiendo PDF: {mensaje}")
"""


def crear_excel_ejemplo_inasistencias(archivo_salida: str):
    """
    Crea un archivo Excel de ejemplo con el formato correcto para inasistencias
    Útil para que los instructores sepan cómo estructurar sus archivos
    """
    datos_ejemplo = [
        {
            'IDENTIFICACIÓN APRENDIZ': 'CC - 1234567890',
            'APRENDIZ': 'JUAN CARLOS PEREZ GOMEZ',
            'FECHA INICIO': '01/12/2024',
            'FECHA FIN': '01/12/2024',
            'JUSTIFICACION': 'EL APRENDIZ NO ASISTIÓ A LA FORMACIÓN TÉCNICA. NO PRESENTO SOPORTES DE LA INASISTENCIA.'
        },
        {
            'IDENTIFICACIÓN APRENDIZ': 'TI - 1058353541',
            'APRENDIZ': 'MARIA FERNANDA RODRIGUEZ LOPEZ',
            'FECHA INICIO': '02/12/2024',
            'FECHA FIN': '02/12/2024',
            'JUSTIFICACION': 'INASISTENCIA JUSTIFICADA POR INCAPACIDAD MÉDICA.'
        },
        {
            'IDENTIFICACIÓN APRENDIZ': 'CC - 1057979354',
            'APRENDIZ': 'DIEGO ALEJANDRO MARTINEZ SANCHEZ',
            'FECHA INICIO': '01/12/2024',
            'FECHA FIN': '03/12/2024',
            'JUSTIFICACION': 'EL APRENDIZ NO ASISTIÓ A LA FORMACIÓN TÉCNICA. NO PRESENTO SOPORTES DE LA INASISTENCIA.'
        },
    ]
    
    df = pd.DataFrame(datos_ejemplo)
    df.to_excel(archivo_salida, index=False, engine='openpyxl')
    logger.info(f"Archivo de ejemplo creado en {archivo_salida}")
    print(f"✅ Archivo de ejemplo creado: {archivo_salida}")


if __name__ == "__main__":
    # Crear archivo de ejemplo para instructores
    crear_excel_ejemplo_inasistencias('ejemplo_inasistencias_sena.xlsx')
    print("\n📄 Estructura del archivo:")
    print("   - IDENTIFICACIÓN APRENDIZ: CC - 1234567890")
    print("   - APRENDIZ: Nombre completo del aprendiz")
    print("   - FECHA INICIO: DD/MM/YYYY")
    print("   - FECHA FIN: DD/MM/YYYY (para inasistencias de varios días)")
    print("   - JUSTIFICACION: Texto explicativo (opcional)")