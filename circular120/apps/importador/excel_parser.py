import pandas as pd
from io import BytesIO, StringIO
from datetime import datetime
import re
import logging

logger = logging.getLogger('importador.parser')

class ExcelParser:
    """
    Parser optimizado para formato SENA específico
    Ahora maneja archivos HTML disfrazados de Excel
    """

    JUSTIFIED_KEYWORDS = [
        "MEDICA", "MEDICO", "CITA", "INCAPACIDAD", "PERMISO",
        "PERSONAL", "ENFERMEDAD", "ENFERMO", "EXCUSA", "JUSTIFICACION", 
        "SOPORTE", "ENTREGA", "PRESENTA", "ADJUNTO", "CERTIFICADO"
    ]

    def __init__(self, archivo):
        self.archivo = archivo
        self.df = None
        self.ficha_numero = None
        self.programa_nombre = None
        self.is_html = False

    def _detect_html(self, content):
        """Detecta si el contenido es HTML"""
        if isinstance(content, bytes):
            content_str = content.decode('utf-8', errors='ignore')[:1000]
        else:
            content_str = str(content)[:1000]
        
        html_indicators = ['<html', '<table', '<tr>', '<td>', '<!DOCTYPE', '<meta']
        return any(indicator in content_str.lower() for indicator in html_indicators)

    def load_file(self):
        """Carga el archivo Excel o HTML"""
        try:
            self.df = self._read_df()
            if self.df is None or self.df.empty:
                logger.error("DataFrame vacío o None")
                return False
            
            # Limpiar el DataFrame
            self.df = self._clean_dataframe(self.df)
            
            # Normalizar nombres de columnas
            self.df.columns = [self._normalize_column_name(col) for col in self.df.columns]
            
            logger.info(f"Archivo cargado {'(HTML detectado)' if self.is_html else '(Excel)'}")
            logger.info(f"Columnas: {list(self.df.columns)}")
            logger.info(f"Total filas: {len(self.df)}")
            
            return True
        except Exception as e:
            logger.exception(f"Error cargando archivo: {e}")
            return False

    def _read_df(self):
        """Lee el archivo Excel o HTML"""
        try:
            if isinstance(self.archivo, str):
                # Es una ruta de archivo
                with open(self.archivo, 'rb') as f:
                    content = f.read()
            else:
                # Es un archivo subido
                if hasattr(self.archivo, 'read'):
                    content = self.archivo.read()
                    self.archivo.seek(0)  # Reset para reusar
                else:
                    content = self.archivo
            
            # Detectar si es HTML
            if self._detect_html(content):
                logger.info("⚠️ Archivo HTML detectado (disfrazado de Excel)")
                self.is_html = True
                return self._read_html(content)
            else:
                # Es Excel real
                return self._read_excel(content)
                    
        except Exception as e:
            logger.exception(f"Error leyendo archivo: {e}")
            raise

    def _read_html(self, content):
        """Lee un archivo HTML y lo convierte a DataFrame"""
        try:
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            # Usar pandas para leer tablas HTML
            tables = pd.read_html(StringIO(content))
            
            if not tables:
                logger.error("No se encontraron tablas en el HTML")
                return None
            
            # Tomar la tabla más grande (probablemente la de datos)
            df = max(tables, key=lambda x: len(x))
            logger.info(f"✅ Tabla HTML extraída: {len(df)} filas")
            
            return df
            
        except Exception as e:
            logger.exception(f"Error leyendo HTML: {e}")
            raise

    def _read_excel(self, content):
        """Lee un archivo Excel real"""
        try:
            name = getattr(self.archivo, 'name', '').lower() if hasattr(self.archivo, 'name') else ''
            bio = BytesIO(content) if isinstance(content, bytes) else content
            
            if name.endswith(('.xlsx', '.xlsm')) or not name:
                return pd.read_excel(bio, engine='openpyxl')
            elif name.endswith('.xls'):
                try:
                    return pd.read_excel(bio, engine='xlrd')
                except:
                    # Si xlrd falla, intentar con openpyxl
                    logger.warning("xlrd falló, intentando con openpyxl")
                    bio.seek(0)
                    return pd.read_excel(bio, engine='openpyxl')
            else:
                # Intentar openpyxl por defecto
                return pd.read_excel(bio, engine='openpyxl')
                    
        except Exception as e:
            logger.exception(f"Error leyendo Excel: {e}")
            raise

    def _clean_dataframe(self, df):
        """Limpia el DataFrame de filas y columnas vacías"""
        # Eliminar filas completamente vacías
        df = df.dropna(how='all')
        
        # Eliminar columnas completamente vacías
        df = df.dropna(axis=1, how='all')
        
        # Eliminar columnas sin nombre o con nombres genéricos
        df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]
        
        # Resetear índice
        df = df.reset_index(drop=True)
        
        return df

    def _normalize_column_name(self, col_name):
        """Normaliza un nombre de columna"""
        if not isinstance(col_name, str):
            return str(col_name).strip().upper()
        
        # Eliminar espacios al inicio y final
        normalized = col_name.strip().upper()
        
        # Remover tildes
        replacements = {
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'á': 'A', 'é': 'E', 'í': 'I', 'ó': 'O', 'ú': 'U',
            'Ñ': 'N', 'ñ': 'N'
        }
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        # Normalizar espacios múltiples
        normalized = ' '.join(normalized.split())
        
        return normalized

    def _find_column(self, possible_names):
        """Encuentra una columna por varios nombres posibles"""
        if not isinstance(possible_names, list):
            possible_names = [possible_names]
        
        # Normalizar nombres posibles
        possible_normalized = [self._normalize_column_name(name) for name in possible_names]
        
        # Primero buscar coincidencia exacta
        for col in self.df.columns:
            col_norm = self._normalize_column_name(col)
            for possible in possible_normalized:
                if col_norm == possible:
                    return col
        
        # Luego buscar coincidencia parcial
        for col in self.df.columns:
            col_norm = self._normalize_column_name(col)
            for possible in possible_normalized:
                if possible in col_norm or col_norm in possible:
                    return col
        
        # Si no encuentra nada, buscar por palabras clave
        for col in self.df.columns:
            col_norm = self._normalize_column_name(col)
            for possible in possible_normalized:
                # Extraer palabras clave principales
                palabras_posibles = possible.split()
                if all(palabra in col_norm for palabra in palabras_posibles if len(palabra) > 3):
                    return col
        
        return None

    def _parse_ficha(self, ficha_str):
        """
        Parsea la columna FICHA que viene en formato:
        '2993648 - ANALISIS Y DESARROLLO DE SOFTWARE.'
        """
        if pd.isna(ficha_str):
            return None, None
        
        ficha_str = str(ficha_str).strip()
        
        # Buscar patrón: NUMERO - NOMBRE
        match = re.match(r'^(\d+)\s*-\s*(.+)$', ficha_str)
        
        if match:
            numero = match.group(1).strip()
            programa = match.group(2).strip().rstrip('.')
            return numero, programa
        
        # Si solo tiene números
        numeros = re.findall(r'\d+', ficha_str)
        if numeros:
            return numeros[0], None
        
        return None, None

    def _parse_documento(self, doc_str):
        """
        Parsea documento que viene en formato:
        'PPT - 6259731' o 'CC - 1234567890'
        """
        if pd.isna(doc_str):
            return "", ""
        
        doc_str = str(doc_str).strip()
        
        # Buscar patrón: TIPO - NUMERO
        match = re.match(r'^([A-Z]+)\s*-\s*(\d+)$', doc_str)
        
        if match:
            tipo = match.group(1).strip()
            numero = match.group(2).strip()
            return tipo, numero
        
        # Si solo tiene números
        numeros = re.findall(r'\d+', doc_str)
        if numeros:
            return "CC", numeros[0]
        
        return "CC", doc_str.replace(' ', '')

    def _parse_date(self, value):
        """Parsea una fecha"""
        if pd.isna(value):
            return None
        
        if isinstance(value, (pd.Timestamp, datetime)):
            return value.date()
        
        try:
            # Intentar parsear con formato día primero
            parsed = pd.to_datetime(value, dayfirst=True, errors='coerce')
            if pd.notna(parsed):
                return parsed.date()
        except:
            pass
        
        return None

    def _split_nombre(self, texto):
        """Divide nombre completo"""
        if pd.isna(texto):
            return "", ""
        
        texto = str(texto).strip()
        partes = texto.split()
        
        if len(partes) == 0:
            return "", ""
        elif len(partes) == 1:
            return partes[0].title(), ""
        elif len(partes) == 2:
            return partes[0].title(), partes[1].title()
        elif len(partes) == 3:
            # Asume: nombre apellido1 apellido2
            return partes[0].title(), ' '.join(partes[1:]).title()
        else:
            # Más de 3: primer nombre + resto apellidos
            return ' '.join(partes[:2]).title(), ' '.join(partes[2:]).title()

    def _is_justified(self, texto):
        """Determina si está justificada"""
        if pd.isna(texto):
            return False
        
        texto_upper = str(texto).upper()
        
        # Si dice explícitamente "NO PRESENTO SOPORTES", NO está justificada
        if "NO PRESENTO" in texto_upper or "NO ASISTIO" in texto_upper:
            return False
        
        # Buscar keywords de justificación
        for keyword in self.JUSTIFIED_KEYWORDS:
            if keyword in texto_upper:
                # Para SOPORTE, verificar que tenga sentido positivo
                if keyword == "SOPORTE":
                    if any(x in texto_upper for x in ["ENTREGA", "PRESENTA", "ADJUNTO", "TIENE"]):
                        return True
                else:
                    return True
        
        return False

    def parse_inasistencias(self):
        """Parsea archivo de inasistencias con formato SENA"""
        if self.df is None:
            return [], ["No se ha cargado ningún archivo"]

        logger.info(f"Iniciando parseo de inasistencias")
        logger.info(f"Columnas disponibles: {list(self.df.columns)}")
        
        # Imprimir columnas normalizadas para debug
        for col in self.df.columns:
            logger.info(f"  Columna original: '{col}' -> Normalizada: '{self._normalize_column_name(col)}'")

        # Mapeo amplio de columnas - incluye muchas variantes
        columnas = {
            'ficha': self._find_column([
                'FICHA', 
                'NUMERO FICHA', 
                'NO FICHA',
                'NUM FICHA',
                'NO. FICHA'
            ]),
            'instructor': self._find_column([
                'INSTRUCTOR', 
                'INSTRUCTOR LIDER',
                'NOMBRE INSTRUCTOR'
            ]),
            'documento': self._find_column([
                'IDENTIFICACION APRENDIZ',
                'IDENTIFICACIÓN APRENDIZ',
                'IDENTIFICACION',
                'DOCUMENTO',
                'CEDULA',
                'CC',
                'DOC APRENDIZ',
                'IDENTIF',
                'NO. DOCUMENTO'
            ]),
            'aprendiz': self._find_column([
                'APRENDIZ',
                'NOMBRE APRENDIZ',
                'NOMBRE',
                'NOMBRES',
                'NOMBRE COMPLETO',
                'NOMBRES Y APELLIDOS'
            ]),
            'fecha_inicio': self._find_column([
                'FECHA INICIO',
                'FECHA_INICIO',
                'FECHA',
                'FECHA INASISTENCIA',
                'DATE',
                'FECHA DE INASISTENCIA'
            ]),
            'fecha_fin': self._find_column([
                'FECHA FIN',
                'FECHA_FIN'
            ]),
            'cant_horas': self._find_column([
                'CANT. HORAS',
                'CANT HORAS',
                'CANT_HORAS',
                'HORAS',
                'CANTIDAD HORAS',
                'CANTIDAD DE HORAS'
            ]),
            'justificacion': self._find_column([
                'JUSTIFICACION',
                'JUSTIFICACIÓN',
                'OBSERVACION',
                'OBSERVACIONES',
                'MOTIVO',
                'COMENTARIO',
                'COMENTARIOS'
            ])
        }

        logger.info(f"Columnas mapeadas:")
        for key, value in columnas.items():
            logger.info(f"  {key}: {value if value else 'NO ENCONTRADA'}")

        # Validar columnas obligatorias
        errores = []
        
        if not columnas['documento']:
            # Intentar encontrar manualmente
            logger.warning("No se encontró columna de documento, buscando manualmente...")
            for col in self.df.columns:
                col_upper = str(col).upper()
                if 'IDENTIF' in col_upper or 'DOCUMENTO' in col_upper or 'CEDULA' in col_upper:
                    columnas['documento'] = col
                    logger.info(f"✅ Columna documento encontrada manualmente: {col}")
                    break
            
            if not columnas['documento']:
                errores.append(f"❌ No se encontró columna de DOCUMENTO/IDENTIFICACIÓN. Columnas disponibles: {', '.join(self.df.columns)}")
        
        if not columnas['fecha_inicio']:
            # Intentar encontrar manualmente
            logger.warning("No se encontró columna de fecha, buscando manualmente...")
            for col in self.df.columns:
                col_upper = str(col).upper()
                if 'FECHA' in col_upper:
                    columnas['fecha_inicio'] = col
                    logger.info(f"✅ Columna fecha encontrada manualmente: {col}")
                    break
            
            if not columnas['fecha_inicio']:
                errores.append(f"❌ No se encontró columna de FECHA. Columnas disponibles: {', '.join(self.df.columns)}")
        
        if errores:
            return [], errores

        registros = []
        filas_procesadas = 0
        filas_omitidas = 0

        for idx, row in self.df.iterrows():
            try:
                fila_excel = idx + 2  # +2 (índice 0 + fila header)
                
                # DOCUMENTO (obligatorio)
                doc_raw = row.get(columnas['documento'])
                if pd.isna(doc_raw):
                    logger.warning(f"Fila {fila_excel}: Documento vacío, omitiendo")
                    filas_omitidas += 1
                    continue
                
                tipo_doc, numero_doc = self._parse_documento(doc_raw)
                if not numero_doc:
                    logger.warning(f"Fila {fila_excel}: No se pudo parsear documento '{doc_raw}', omitiendo")
                    filas_omitidas += 1
                    continue
                
                # FECHA (obligatorio)
                fecha_raw = row.get(columnas['fecha_inicio'])
                fecha = self._parse_date(fecha_raw)
                if not fecha:
                    errores.append(f"Fila {fila_excel}: Fecha inválida '{fecha_raw}'")
                    filas_omitidas += 1
                    continue
                
                # FICHA
                numero_ficha = None
                programa_nombre = None
                if columnas['ficha']:
                    ficha_raw = row.get(columnas['ficha'])
                    if pd.notna(ficha_raw):
                        numero_ficha, programa_nombre = self._parse_ficha(ficha_raw)
                
                # APRENDIZ
                nombre = ""
                apellido = ""
                if columnas['aprendiz']:
                    aprendiz_raw = row.get(columnas['aprendiz'])
                    if pd.notna(aprendiz_raw):
                        nombre, apellido = self._split_nombre(aprendiz_raw)
                
                # INSTRUCTOR
                instructor = ""
                if columnas['instructor'] and pd.notna(row.get(columnas['instructor'])):
                    instructor = str(row.get(columnas['instructor'])).strip()
                
                # HORAS
                cant_horas = None
                if columnas['cant_horas'] and pd.notna(row.get(columnas['cant_horas'])):
                    try:
                        cant_horas = float(row.get(columnas['cant_horas']))
                    except:
                        pass
                
                # JUSTIFICACIÓN
                observacion = ""
                if columnas['justificacion'] and pd.notna(row.get(columnas['justificacion'])):
                    observacion = str(row.get(columnas['justificacion'])).strip()
                
                justificada = self._is_justified(observacion)
                
                registro = {
                    'fila_excel': fila_excel,
                    'tipo_documento': tipo_doc,
                    'documento': numero_doc,
                    'nombre': nombre,
                    'apellido': apellido,
                    'numero_ficha': numero_ficha,
                    'programa_nombre': programa_nombre,
                    'instructor': instructor,
                    'fecha': fecha,
                    'cant_horas': cant_horas,
                    'observacion': observacion,
                    'justificada': justificada,
                }
                
                registros.append(registro)
                filas_procesadas += 1
                
                if filas_procesadas <= 3:  # Log primeros 3 registros
                    logger.info(f"✅ Fila {fila_excel}: Doc={tipo_doc}-{numero_doc}, Nombre={nombre} {apellido}, Ficha={numero_ficha}, Fecha={fecha}")
                
            except Exception as e:
                logger.exception(f"Error en fila {idx + 2}: {e}")
                errores.append(f"Fila {idx + 2}: {str(e)}")
                filas_omitidas += 1

        logger.info(f"Parseo completado: {filas_procesadas} procesadas, {filas_omitidas} omitidas")
        
        if filas_procesadas == 0 and not errores:
            errores.append("No se procesó ninguna fila. Verifica que el archivo tenga datos válidos.")
        
        return registros, errores

    def parse_evaluaciones(self):
        """Parsea archivo de evaluaciones"""
        if self.df is None:
            return [], ["No se ha cargado ningún archivo"]

        logger.info(f"Iniciando parseo de evaluaciones")

        # Mapeo de columnas
        columnas = {
            'ficha': self._find_column(['FICHA', 'NO. FICHA']),
            'documento': self._find_column(['IDENTIFICACION APRENDIZ', 'DOCUMENTO', 'IDENTIFICACION']),
            'aprendiz': self._find_column(['APRENDIZ', 'NOMBRE', 'NOMBRES Y APELLIDOS']),
            'ra_codigo': self._find_column(['CODIGO RA', 'RA', 'RESULTADO APRENDIZAJE']),
            'juicio': self._find_column(['JUICIO', 'JUICIO EVALUATIVO', 'ESTADO']),
            'fecha': self._find_column(['FECHA EVALUACION', 'FECHA']),
        }

        # Validar obligatorias
        errores = []
        if not columnas['documento']:
            errores.append("No se encontró columna de DOCUMENTO")
        if not columnas['ra_codigo']:
            errores.append("No se encontró columna de CÓDIGO RA")
        if not columnas['juicio']:
            errores.append("No se encontró columna de JUICIO")
        
        if errores:
            return [], errores

        registros = []

        for idx, row in self.df.iterrows():
            try:
                fila_excel = idx + 2
                
                # Documento
                tipo_doc, numero_doc = self._parse_documento(row.get(columnas['documento']))
                if not numero_doc:
                    continue
                
                # RA
                ra_codigo = str(row.get(columnas['ra_codigo'])).strip() if pd.notna(row.get(columnas['ra_codigo'])) else ""
                if not ra_codigo:
                    errores.append(f"Fila {fila_excel}: Código RA vacío")
                    continue
                
                # Juicio
                juicio_raw = str(row.get(columnas['juicio'])).strip().upper() if pd.notna(row.get(columnas['juicio'])) else ""
                
                # Normalizar juicio
                if 'APROB' in juicio_raw or juicio_raw == 'SI':
                    juicio = 'APROBADO'
                elif 'NO' in juicio_raw or 'REPROB' in juicio_raw:
                    juicio = 'NO_APROBADO'
                else:
                    juicio = 'PENDIENTE'
                
                # Nombre
                nombre = ""
                apellido = ""
                if columnas['aprendiz']:
                    nombre, apellido = self._split_nombre(row.get(columnas['aprendiz']))
                
                # Ficha
                numero_ficha = None
                if columnas['ficha']:
                    numero_ficha, _ = self._parse_ficha(row.get(columnas['ficha']))
                
                # Fecha
                fecha_evaluacion = None
                if columnas['fecha']:
                    fecha_evaluacion = self._parse_date(row.get(columnas['fecha']))
                
                registro = {
                    'fila_excel': fila_excel,
                    'tipo_documento': tipo_doc,
                    'documento': numero_doc,
                    'nombre': nombre,
                    'apellido': apellido,
                    'numero_ficha': numero_ficha,
                    'ra_codigo': ra_codigo,
                    'juicio': juicio,
                    'fecha_evaluacion': fecha_evaluacion,
                }
                
                registros.append(registro)
                
            except Exception as e:
                logger.exception(f"Error en fila {idx + 2}: {e}")
                errores.append(f"Fila {idx + 2}: {str(e)}")

        return registros, errores