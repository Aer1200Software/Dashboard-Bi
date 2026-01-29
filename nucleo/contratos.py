from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class EsquemaDatosVentas:
    """
    Define el esquema estándar que el dashboard espera para la tabla de ventas.

    Importante:
    - El dashboard internamente trabaja con nombres en español.
    - Si el CSV viene con nombres distintos (ej. 'date', 'qty'), se normaliza.
    """

    # Columnas estándar internas (en español)
    columnas_requeridas: List[str]

    # Mapeo de alias -> nombre_estandar
    # Ejemplo: {"date": "fecha", "qty": "cantidad"}
    alias_a_estandar: Dict[str, str]

    # Columnas opcionales (no son obligatorias, pero si están se usan)
    columnas_opcionales: List[str]

    @staticmethod
    def esquema_por_defecto() -> "EsquemaDatosVentas":
        """
        Esquema mínimo recomendado para el MVP del dashboard.
        """
        columnas_requeridas = [
            "fecha",
            "id_orden",
            "id_cliente",
            "id_producto",
            "cantidad",
            "precio",
            "costo",
            "region",
            "canal",
        ]

        alias_a_estandar = {
            # Fecha
            "date": "fecha",
            "fecha": "fecha",

            # IDs
            "order_id": "id_orden",
            "id_orden": "id_orden",
            "customer_id": "id_cliente",
            "id_cliente": "id_cliente",
            "product_id": "id_producto",
            "id_producto": "id_producto",

            # Cantidades y valores
            "qty": "cantidad",
            "cantidad": "cantidad",
            "price": "precio",
            "precio": "precio",
            "cost": "costo",
            "costo": "costo",

            # Dimensiones
            "region": "region",
            "región": "region",
            "canal": "canal",
            "channel": "canal",
        }

        columnas_opcionales = [
            "estado",          # por ejemplo: completada/cancelada
            "categoria",       # categoría del producto/servicio
            "nombre_producto", # si tienes una dimensión más descriptiva
        ]

        return EsquemaDatosVentas(
            columnas_requeridas=columnas_requeridas,
            alias_a_estandar=alias_a_estandar,
            columnas_opcionales=columnas_opcionales,
        )


@dataclass
class ResultadoValidacion:
    """
    Resultado de validar un dataset.
    - 'es_valido' indica si se puede continuar.
    - 'errores' lista de mensajes para el usuario.
    - 'advertencias' lista de cosas no críticas.
    """
    es_valido: bool
    errores: List[str]
    advertencias: List[str]


class FuenteDatos(ABC):
    """
    Contrato para fuentes de datos (CSV, Base de Datos, API, etc.)
    Cualquier fuente debe devolver un DataFrame en el esquema estándar.
    """

    @abstractmethod
    def cargar(self) -> pd.DataFrame:
        """
        Retorna un DataFrame crudo (aún no transformado).
        La normalización/validación puede hacerse dentro de la fuente o después,
        según la arquitectura que elijas.
        """
        raise NotImplementedError
