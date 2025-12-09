import pandas as pd
from datetime import timedelta
import re
from typing import Dict, List, Tuple, Optional
import logging
import os

logger = logging.getLogger('importador')


class ExcelParser:

    DOCUMENTO_PATTERNS = [r'identificaci[oó]n', r'documento', r'cc', r'cedula']
    NOMBRE_COMPLETO_PATTERNS = [r'^aprendiz$', r'nombre']
    FECHA_INICIO_PATTERNS = [r'fecha.*inicio', r'fecha']
    FECHA_FIN_PATTERNS = [r'fecha.*fin']
    JUSTIFICACION_PATTERNS = [r'justificacion']
    FICHA_PATTERNS = [r'ficha']

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df = None
        self.detected_columns = {}

    def load_file(self) -> bool:
        try:
            self.df = pd.read_excel(self.file_path)
            return True
        except Exception as e:
            logger.error(e)
            return False

    def _match_column(self, patterns: List[str], available_columns: List[str]) -> Optional[str]:
        for col in available_columns:
            for pattern in patterns:
                if re.search(pattern, col.lower()):
                    return col
        return None

    def detect_columns_inasistencias(self) -> Dict[str, str]:
        columns = self.df.columns.tolist()
        detected = {
            'documento': self._match_column(self.DOCUMENTO_PATTERNS, columns),
            'nombre': self._match_column(self.NOMBRE_COMPLETO_PATTERNS, columns),
            'fecha_inicio': self._match_column(self.FECHA_INICIO_PATTERNS, columns),
            'fecha_fin': self._match_column(self.FECHA_FIN_PATTERNS, columns),
            'justificacion': self._match_column(self.JUSTIFICACION_PATTERNS, columns),
            'ficha': self._match_column(self.FICHA_PATTERNS, columns),
        }
        self.detected_columns = detected
        return detected

    def parse_inasistencias(self) -> Tuple[List[Dict], List[str]]:
        registros = []
        errores = []

        cols = self.detect_columns_inasistencias()

        for idx, row in self.df.iterrows():
            try:
                documento = str(row[cols['documento']]).strip()

                ficha_raw = str(row[cols['ficha']]).strip()
                partes = ficha_raw.split('-', 1)

                numero_ficha = partes[0].strip()
                nombre_programa = partes[1].strip() if len(partes) > 1 else ''

                fecha_inicio = pd.to_datetime(row[cols['fecha_inicio']]).date()

                fecha_fin = None
                if cols.get('fecha_fin') and not pd.isna(row[cols['fecha_fin']]):
                    fecha_fin = pd.to_datetime(row[cols['fecha_fin']]).date()

                justificada = False
                if cols.get('justificacion') and not pd.isna(row[cols['justificacion']]):
                    justificada = str(row[cols['justificacion']]).lower() in ['si', 'sí']

                if fecha_fin:
                    fecha_actual = fecha_inicio
                    while fecha_actual <= fecha_fin:
                        registros.append({
                            'documento': documento,
                            'numero_ficha': numero_ficha,
                            'nombre_programa': nombre_programa,
                            'fecha': fecha_actual,
                            'justificada': justificada,
                            'fila_excel': idx + 2,
                        })
                        fecha_actual += timedelta(days=1)
                else:
                    registros.append({
                        'documento': documento,
                        'numero_ficha': numero_ficha,
                        'nombre_programa': nombre_programa,
                        'fecha': fecha_inicio,
                        'justificada': justificada,
                        'fila_excel': idx + 2,
                    })

            except Exception as e:
                errores.append(f"Fila {idx + 2}: {str(e)}")

        return registros, errores
