import pandas as pd
from io import BytesIO
from datetime import datetime
import re
import logging

logger = logging.getLogger('importador.parser')

class ExcelParser:
    """
    Parser que acepta .xls .xlsx .xlsm y devuelve una lista de registros
    Cada registro:
      - documento (str)
      - numero_ficha (str)
      - instructor (str)
      - nombre (str)
      - apellido (str)
      - fecha (date)   <-- usamos FECHA INICIO
      - cant_horas (float | None)
      - observacion (str)
      - justificada (bool)  <-- aplica Regla 1
      - fila_excel (int)
    """

    # columnas esperadas (normalizadas a mayúsculas sin tildes)
    EXPECTED = {
        'FICHA': 'FICHA',
        'INSTRUCTOR': 'INSTRUCTOR',
        'IDENTIFICACIÓN APRENDIZ': 'IDENTIFICACION APRENDIZ',
        'APRENDIZ': 'APRENDIZ',
        'FECHA INICIO': 'FECHA INICIO',
        'FECHA FIN': 'FECHA FIN',
        'CANT. HORAS': 'CANT HORAS',
        'JUSTIFICACION': 'JUSTIFICACION'
    }

    JUSTIFIED_KEYWORDS = [
        "MEDICA", "MEDICO", "CITA", "INCAPACIDAD", "PERMISO",
        "PERSONAL", "ENFERMEDAD", "ENFERMO", "EXCUSA", "JUSTIFICACION", "SOPORTE"
    ]

    def __init__(self, archivo):
        self.archivo = archivo

    def _read_df(self):
        name = getattr(self.archivo, "name", "")
        name = name.lower()
        try:
            if isinstance(self.archivo, str):
                if name.endswith((".xlsx", ".xlsm")):
                    return pd.read_excel(self.archivo, engine="openpyxl")
                elif name.endswith(".xls"):
                    return pd.read_excel(self.archivo, engine="xlrd")
                else:
                    raise ValueError("Formato no soportado")
            else:
                content = self.archivo.read()
                bio = BytesIO(content)
                if name.endswith((".xlsx", ".xlsm")):
                    return pd.read_excel(bio, engine="openpyxl")
                elif name.endswith(".xls"):
                    return pd.read_excel(bio, engine="xlrd")
                else:
                    raise ValueError("Formato no soportado. Use .xls .xlsx o .xlsm")
        except Exception as e:
            logger.exception("Error leyendo Excel: %s", e)
            raise

    def _norm_col(self, s):
        if not isinstance(s, str):
            return s
        s2 = s.strip().upper()
        # quitar tildes básicas
        s2 = s2.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")
        s2 = s2.replace("Ñ", "N")
        s2 = s2.replace(".", "").replace("(", "").replace(")", "")
        return s2

    def _normalize_df(self, df):
        df.rename(columns={c: self._norm_col(c) for c in df.columns}, inplace=True)
        return df

    def _parse_date(self, v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, (pd.Timestamp, datetime)):
            return v.date()
        try:
            parsed = pd.to_datetime(v, errors='coerce', dayfirst=True)
            if pd.isna(parsed):
                return None
            return parsed.date()
        except Exception:
            return None

    def _split_aprendiz(self, texto):
        if not texto or (isinstance(texto, float) and pd.isna(texto)):
            return "", ""
        texto = str(texto).strip()
        parts = texto.split()
        if len(parts) == 1:
            return parts[0].title(), ""
        nombre = " ".join(parts[:-1]).title()
        apellido = parts[-1].title()
        return nombre, apellido

    def _clean_documento(self, texto):
        if texto is None:
            return ""
        texto = str(texto).strip()
        m = re.search(r'\d{4,}', texto.replace('.', '').replace('-', ''))
        if m:
            return m.group(0)
        return texto.replace(" ", "")

    def _is_justified_text(self, texto):
        if not texto or (isinstance(texto, float) and pd.isna(texto)):
            return False
        t = str(texto).upper()
        # If contains any keyword => justified
        for kw in self.JUSTIFIED_KEYWORDS:
            if kw in t:
                # special: if keyword is SOPORTE, ensure it indicates presence of support
                if kw == "SOPORTE":
                    # phrases that indicate support present
                    if "ENTREGA" in t or "PRESENTA" in t or "TIENE SOPORTE" in t:
                        return True
                    else:
                        continue
                return True
        return False

    def parse_inasistencias(self):
        try:
            df = self._read_df()
        except Exception as e:
            return [], [f"Error al leer el archivo Excel: {e}"]

        df = self._normalize_df(df)

        # Required columns check
        required = ['FICHA', 'IDENTIFICACION APRENDIZ', 'APRENDIZ', 'FECHA INICIO']
        missing = [c for c in required if c not in df.columns]
        if missing:
            return [], [f"Faltan columnas obligatorias: {', '.join(missing)}"]

        registros = []
        for idx, row in df.iterrows():
            fila_num = idx + 2
            try:
                # FICHA -> extraer número antes del guion
                ficha_raw = row.get('FICHA', "")
                numero_ficha = ""
                if isinstance(ficha_raw, (int, float)) and not pd.isna(ficha_raw):
                    numero_ficha = str(int(ficha_raw))
                else:
                    ficha_raw_str = str(ficha_raw).strip()
                    if "-" in ficha_raw_str:
                        numero_ficha = ficha_raw_str.split("-", 1)[0].strip()
                    else:
                        numero_ficha = ficha_raw_str.split()[0].strip()

                documento = self._clean_documento(row.get('IDENTIFICACION APRENDIZ', ""))
                nombres_text = row.get('APRENDIZ', "")
                nombre, apellido = self._split_aprendiz(nombres_text)

                instructor = row.get('INSTRUCTOR', "")
                instructor = "" if (isinstance(instructor, float) and pd.isna(instructor)) else str(instructor).strip()

                fecha = self._parse_date(row.get('FECHA INICIO'))
                # FECHA FIN la ignoramos (usamos FECHA INICIO)
                cant_horas = None
                # posibles nombres: 'CANT HORAS', 'CANT. HORAS'
                if 'CANT HORAS' in df.columns:
                    val = row.get('CANT HORAS')
                elif 'CANT. HORAS' in df.columns:
                    val = row.get('CANT. HORAS')
                else:
                    val = row.get('CANT HORAS', None)
                if val is not None and not (isinstance(val, float) and pd.isna(val)):
                    try:
                        cant_horas = float(val)
                    except Exception:
                        cant_horas = None

                observacion = row.get('JUSTIFICACION', "")
                observacion = "" if (isinstance(observacion, float) and pd.isna(observacion)) else str(observacion).strip()

                justificada = self._is_justified_text(observacion)

                registro = {
                    "fila_excel": fila_num,
                    "documento": documento,
                    "numero_ficha": numero_ficha,
                    "instructor": instructor,
                    "nombre": nombre,
                    "apellido": apellido,
                    "fecha": fecha,
                    "cant_horas": cant_horas,
                    "observacion": observacion,
                    "justificada": justificada,
                }
                registros.append(registro)
            except Exception as e:
                logger.exception("Error procesando fila %s: %s", fila_num, e)
                # seguimos con la siguiente fila
                continue

        return registros, []