from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Tuple

import pandas as pd


@dataclass
class FiltroSeleccion:
    """
    Representa los filtros elegidos por el usuario.
    """
    fecha_inicio: pd.Timestamp
    fecha_fin: pd.Timestamp
    region: Optional[str] = None
    canal: Optional[str] = None
    id_producto: Optional[str] = None


class FiltroDatos:
    """
    Aplica filtros sobre el DataFrame sin modificar el original.
    """

    def aplicar(self, tabla: pd.DataFrame, filtros: FiltroSeleccion) -> pd.DataFrame:
        tabla_filtrada = tabla.copy()

        # Filtro por fechas
        tabla_filtrada = tabla_filtrada[
            (tabla_filtrada["fecha"] >= filtros.fecha_inicio) &
            (tabla_filtrada["fecha"] <= filtros.fecha_fin)
        ]

        # Filtro por región
        if filtros.region and filtros.region != "Todas":
            tabla_filtrada = tabla_filtrada[tabla_filtrada["region"] == filtros.region]

        # Filtro por canal
        if filtros.canal and filtros.canal != "Todos":
            tabla_filtrada = tabla_filtrada[tabla_filtrada["canal"] == filtros.canal]

        # Filtro por producto
        if filtros.id_producto and filtros.id_producto != "Todos":
            tabla_filtrada = tabla_filtrada[tabla_filtrada["id_producto"] == filtros.id_producto]

        return tabla_filtrada


class ComparadorPeriodos:
    """
    Compara métricas del período actual contra el período anterior equivalente.
    """

    def obtener_periodos(
        self,
        fecha_inicio: pd.Timestamp,
        fecha_fin: pd.Timestamp
    ) -> Tuple[Tuple[pd.Timestamp, pd.Timestamp], Tuple[pd.Timestamp, pd.Timestamp]]:
        """
        Devuelve:
        - (inicio_actual, fin_actual)
        - (inicio_anterior, fin_anterior)
        """
        duracion = fecha_fin - fecha_inicio
        inicio_anterior = fecha_inicio - duracion - timedelta(days=1)
        fin_anterior = fecha_inicio - timedelta(days=1)

        return (
            (fecha_inicio, fecha_fin),
            (inicio_anterior, fin_anterior),
        )

    def comparar_metricas(
        self,
        valor_actual: float,
        valor_anterior: float
    ) -> dict:
        """
        Calcula variación absoluta y porcentual.
        """
        diferencia = valor_actual - valor_anterior
        variacion_pct = (
            (diferencia / valor_anterior) * 100
            if valor_anterior != 0 else 0.0
        )

        return {
            "actual": valor_actual,
            "anterior": valor_anterior,
            "diferencia": diferencia,
            "variacion_pct": variacion_pct,
        }
