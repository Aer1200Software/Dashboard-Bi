from __future__ import annotations

import re
from typing import Dict

import pandas as pd

from nucleo.contratos import EsquemaDatosVentas


class NormalizadorColumnas:
    """
    Normaliza el nombre de las columnas y las convierte al esquema estándar.

    Ejemplos:
    - ' date ' -> 'date'
    - 'Región' -> 'region'
    - 'qty' -> 'cantidad'
    """

    def __init__(self, esquema: EsquemaDatosVentas):
        self.esquema = esquema

    @staticmethod
    def _limpiar_nombre_columna(nombre: str) -> str:
        """
        Limpieza base:
        - trim
        - minúsculas
        - quita múltiples espacios
        - reemplaza espacios por guion bajo (solo si existieran)
        """
        nombre = nombre.strip().lower()
        nombre = re.sub(r"\s+", " ", nombre)  # colapsa espacios
        nombre = nombre.replace(" ", "_")
        return nombre

    def _construir_mapa_renombre(self, columnas_originales) -> Dict[str, str]:
        """
        Construye un dict {col_original: col_estandar} según alias_a_estandar.
        """
        mapa = {}
        for col in columnas_originales:
            col_limpia = self._limpiar_nombre_columna(col)

            # Si la columna limpia está en alias, renombramos al estándar
            if col_limpia in self.esquema.alias_a_estandar:
                mapa[col] = self.esquema.alias_a_estandar[col_limpia]
            else:
                # Si no está en alias, la dejamos en su forma limpia (por si es opcional)
                mapa[col] = col_limpia

        return mapa

    def normalizar(self, tabla: pd.DataFrame) -> pd.DataFrame:
        """
        Devuelve una nueva tabla con columnas normalizadas al estándar.
        """
        tabla = tabla.copy()

        # Renombrar según alias
        mapa_renombre = self._construir_mapa_renombre(tabla.columns)
        tabla = tabla.rename(columns=mapa_renombre)

        return tabla
