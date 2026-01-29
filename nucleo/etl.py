from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


@dataclass
class ResultadoLimpieza:
    """
    Reporte simple de limpieza:
    - filas_eliminadas: cuántas filas removimos por inválidas
    - advertencias: mensajes útiles para mostrar en UI si quieres
    """
    filas_eliminadas: int
    advertencias: List[str]


class LimpiadorDatos:
    """
    Limpieza básica y segura:
    - Convierte columnas numéricas a número
    - Maneja nulos
    - Elimina filas inválidas (por ejemplo sin fecha o cantidad negativa si no se permite)
    """

    def limpiar(self, tabla: pd.DataFrame) -> tuple[pd.DataFrame, ResultadoLimpieza]:
        tabla = tabla.copy()
        advertencias: List[str] = []
        filas_iniciales = len(tabla)

        # 1) Fecha: convertir y eliminar filas sin fecha válida
        tabla["fecha"] = pd.to_datetime(tabla["fecha"], errors="coerce")
        filas_sin_fecha = tabla["fecha"].isna().sum()
        if filas_sin_fecha > 0:
            advertencias.append(
                f"Se encontraron {filas_sin_fecha} filas con 'fecha' inválida; fueron eliminadas."
            )
        tabla = tabla.dropna(subset=["fecha"])

        # 2) Convertir numéricos (cantidad, precio, costo)
        for col in ["cantidad", "precio", "costo"]:
            tabla[col] = pd.to_numeric(tabla[col], errors="coerce")

            nulos = tabla[col].isna().sum()
            if nulos > 0:
                advertencias.append(
                    f"Se encontraron {nulos} valores no numéricos/vacíos en '{col}'; se reemplazaron por 0."
                )
                tabla[col] = tabla[col].fillna(0)

        # 3) Reglas básicas de sentido (ajustables)
        # Cantidad negativa: normalmente es error, pero podría ser devolución.
        # Por ahora, eliminamos filas con cantidad < 0.
        negativas = (tabla["cantidad"] < 0).sum()
        if negativas > 0:
            advertencias.append(
                f"Se encontraron {negativas} filas con 'cantidad' negativa; fueron eliminadas."
            )
            tabla = tabla[tabla["cantidad"] >= 0]

        # Precio o costo negativo: muy raro. Eliminamos.
        precio_neg = (tabla["precio"] < 0).sum()
        costo_neg = (tabla["costo"] < 0).sum()
        if precio_neg > 0:
            advertencias.append(
                f"Se encontraron {precio_neg} filas con 'precio' negativo; fueron eliminadas."
            )
            tabla = tabla[tabla["precio"] >= 0]

        if costo_neg > 0:
            advertencias.append(
                f"Se encontraron {costo_neg} filas con 'costo' negativo; fueron eliminadas."
            )
            tabla = tabla[tabla["costo"] >= 0]

        filas_finales = len(tabla)
        filas_eliminadas = filas_iniciales - filas_finales

        return tabla, ResultadoLimpieza(
            filas_eliminadas=filas_eliminadas,
            advertencias=advertencias
        )


class TransformadorVentas:
    """
    Crea columnas derivadas necesarias para BI:
    - ingresos = cantidad * precio
    - costo_total = cantidad * costo
    - margen = ingresos - costo_total
    """

    def transformar(self, tabla: pd.DataFrame) -> pd.DataFrame:
        tabla = tabla.copy()

        tabla["ingresos"] = tabla["cantidad"] * tabla["precio"]
        tabla["costo_total"] = tabla["cantidad"] * tabla["costo"]
        tabla["margen"] = tabla["ingresos"] - tabla["costo_total"]

        # margen_porcentaje (útil para análisis)
        tabla["margen_porcentaje"] = 0.0
        mask = tabla["ingresos"] > 0
        tabla.loc[mask, "margen_porcentaje"] = tabla.loc[mask, "margen"] / tabla.loc[mask, "ingresos"]

        return tabla
