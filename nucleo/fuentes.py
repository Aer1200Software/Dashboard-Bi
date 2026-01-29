from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, BinaryIO, List, Any

import pandas as pd

from nucleo.configuracion import ConfiguracionAplicacion
from nucleo.contratos import FuenteDatos, EsquemaDatosVentas
from nucleo.normalizacion import NormalizadorColumnas
from nucleo.validacion import ValidadorEsquemaCSV


# =========================
# EXCEPCIONES CONTROLADAS
# =========================

class ErrorFuenteDatos(Exception):
    """Error general al cargar datos desde cualquier fuente."""
    pass


class ErrorValidacionDatos(ErrorFuenteDatos):
    """Error cuando el archivo no cumple el esquema requerido."""

    def __init__(self, errores: List[str]):
        self.errores = errores
        super().__init__("El archivo no cumple el esquema requerido.")


# =========================
# FUENTE DE DATOS CSV
# =========================

@dataclass
class FuenteDatosCSV(FuenteDatos):
    """
    Fuente de datos basada en archivos CSV.

    Flujo:
    1) Lee CSV (subido o por defecto) con tolerancia de codificación y separadores
    2) Normaliza columnas al esquema estándar
    3) Valida estructura y tipos
    4) Devuelve DataFrame listo para ETL
    """

    configuracion: ConfiguracionAplicacion
    esquema: EsquemaDatosVentas
    archivo_subido: Optional[BinaryIO] = None
    raiz_proyecto: Optional[Path] = None

    def cargar(self) -> pd.DataFrame:
        # 1) Leer CSV (tolerante a encoding y separadores)
        tabla = self._leer_csv()

        # 2) Normalizar columnas
        normalizador = NormalizadorColumnas(self.esquema)
        tabla = normalizador.normalizar(tabla)

        # 3) Validar esquema y tipos
        validador = ValidadorEsquemaCSV(self.esquema, self.configuracion)
        resultado = validador.validar(tabla)

        if not resultado.es_valido:
            raise ErrorValidacionDatos(resultado.errores)

        return tabla

    def _leer_csv(self) -> pd.DataFrame:
        """
        Lee el archivo del usuario o el CSV por defecto.

        Maneja:
        - Distintas codificaciones (utf-8, utf-8-sig, cp1252, latin-1)
        - Separadores comunes (',' y ';')
        """
        try:
            if self.archivo_subido is not None:
                return self._leer_csv_con_tolerancia(self.archivo_subido)

            ruta = self.configuracion.ruta_csv_absoluta(self.raiz_proyecto)
            return self._leer_csv_con_tolerancia(ruta)

        except FileNotFoundError:
            raise ErrorFuenteDatos(
                f"No se encontró el archivo CSV por defecto en: {self.configuracion.ruta_csv_por_defecto}"
            )
        except Exception as e:
            raise ErrorFuenteDatos(f"No se pudo leer el archivo CSV: {e}") from e

    def _leer_csv_con_tolerancia(self, fuente: Any) -> pd.DataFrame:
        """
        Intenta leer CSV con diferentes codificaciones y separadores.

        'fuente' puede ser:
        - ruta (Path/str)
        - archivo subido por Streamlit (UploadedFile)
        """
        codificaciones = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
        separadores = [",", ";"]

        ultimo_error: Optional[Exception] = None

        for sep in separadores:
            for enc in codificaciones:
                try:
                    # Nota: engine="python" ayuda en algunos CSV problemáticos con separador
                    return pd.read_csv(fuente, encoding=enc, sep=sep, engine="python")
                except Exception as e:
                    ultimo_error = e

        # Si nada funcionó, lanzamos el último error con detalle
        if ultimo_error is not None:
            raise ultimo_error

        raise ErrorFuenteDatos("No se pudo leer el CSV por un error desconocido.")
