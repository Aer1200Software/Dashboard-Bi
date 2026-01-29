from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

import pandas as pd

from nucleo.contratos import EsquemaDatosVentas, ResultadoValidacion
from nucleo.configuracion import ConfiguracionAplicacion


class ValidadorEsquemaCSV:
    """
    Valida que un DataFrame cumpla el esquema mínimo para el dashboard.
    - Columnas requeridas
    - Tipos convertibles (fecha y numéricos)
    - Límites (max filas) para evitar problemas de memoria
    """

    def __init__(self, esquema: EsquemaDatosVentas, config: ConfiguracionAplicacion):
        self.esquema = esquema
        self.config = config

    def validar(self, tabla: pd.DataFrame) -> ResultadoValidacion:
        errores: List[str] = []
        advertencias: List[str] = []

        # 1) Validar tamaño
        if len(tabla) > self.config.max_filas_csv:
            errores.append(
                f"El archivo tiene {len(tabla):,} filas y excede el máximo permitido "
                f"({self.config.max_filas_csv:,}). Usa un archivo más pequeño o filtra los datos."
            )
            return ResultadoValidacion(es_valido=False, errores=errores, advertencias=advertencias)

        # 2) Validar columnas requeridas
        columnas_presentes = set(tabla.columns)
        faltantes = [c for c in self.esquema.columnas_requeridas if c not in columnas_presentes]
        if faltantes:
            errores.append(
                "Faltan columnas requeridas en el archivo: "
                + ", ".join(faltantes)
                + "."
            )

        # Si faltan columnas críticas, no vale la pena seguir con tipos
        if errores:
            return ResultadoValidacion(es_valido=False, errores=errores, advertencias=advertencias)

        # 3) Validar que 'fecha' sea convertible
        if not self._columna_fecha_convertible(tabla, "fecha"):
            errores.append(
                "La columna 'fecha' no se pudo convertir a formato fecha. "
                "Asegúrate de que tenga valores como '2025-01-31' o '31/01/2025'."
            )

        # 4) Validar numéricos (cantidad, precio, costo)
        for col_num in ["cantidad", "precio", "costo"]:
            if not self._columna_numerica_convertible(tabla, col_num):
                errores.append(
                    f"La columna '{col_num}' no se pudo convertir a número. "
                    "Revisa que no tenga texto o símbolos."
                )

        # 5) Advertencias útiles (no bloquean)
        if tabla["cantidad"].isna().any():
            advertencias.append("Hay valores vacíos en 'cantidad'. Se tratarán como 0 si se limpia el dataset.")
        if tabla["precio"].isna().any():
            advertencias.append("Hay valores vacíos en 'precio'. Se tratarán como 0 si se limpia el dataset.")
        if tabla["costo"].isna().any():
            advertencias.append("Hay valores vacíos en 'costo'. Se tratarán como 0 si se limpia el dataset.")

        # 6) Validaciones de sentido (básicas)
        if (tabla["cantidad"] < 0).any():
            advertencias.append("Se detectaron cantidades negativas. Revisa si son devoluciones o errores.")
        if (tabla["precio"] < 0).any():
            advertencias.append("Se detectaron precios negativos. Revisa el CSV.")
        if (tabla["costo"] < 0).any():
            advertencias.append("Se detectaron costos negativos. Revisa el CSV.")

        es_valido = len(errores) == 0
        return ResultadoValidacion(es_valido=es_valido, errores=errores, advertencias=advertencias)

    def _columna_fecha_convertible(self, tabla: pd.DataFrame, columna: str) -> bool:
        try:
            if self.config.formato_fecha:
                pd.to_datetime(tabla[columna], format=self.config.formato_fecha, errors="raise")
            else:
                pd.to_datetime(tabla[columna], errors="raise")
            return True
        except Exception:
            return False

    @staticmethod
    def _columna_numerica_convertible(tabla: pd.DataFrame, columna: str) -> bool:
        try:
            pd.to_numeric(tabla[columna], errors="raise")
            return True
        except Exception:
            return False
