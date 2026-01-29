from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression


@dataclass
class ResultadoPronostico:
    """
    Resultado del pronóstico:
    - tabla: dataframe con fechas reales y futuras
    - modelo: modelo entrenado (por si luego quieres métricas)
    """
    tabla: pd.DataFrame
    modelo: LinearRegression


class PronosticadorVentasLineal:
    """
    Pronóstico de ingresos usando regresión lineal simple.
    Trabaja con ingresos agregados por día.
    """

    def entrenar_y_pronosticar(
        self,
        tabla: pd.DataFrame,
        dias_futuros: int = 30
    ) -> ResultadoPronostico:
        """
        Retorna una tabla con:
        - fecha
        - ingresos_reales
        - ingresos_pronosticados
        """

        if tabla.empty:
            raise ValueError("No hay datos para generar pronóstico.")

        # 1) Agregar ingresos por día
        diario = (
            tabla.groupby("fecha", as_index=False)
            .agg(ingresos=("ingresos", "sum"))
            .sort_values("fecha")
        )

        # 2) Convertir fechas a índice numérico
        diario["dia_idx"] = np.arange(len(diario))

        X = diario[["dia_idx"]]
        y = diario["ingresos"]

        # 3) Entrenar modelo
        modelo = LinearRegression()
        modelo.fit(X, y)

        # 4) Crear rango futuro
        ultimo_idx = diario["dia_idx"].max()
        idx_futuro = np.arange(ultimo_idx + 1, ultimo_idx + dias_futuros + 1)

        fechas_futuras = pd.date_range(
            start=diario["fecha"].max() + pd.Timedelta(days=1),
            periods=dias_futuros,
            freq="D"
        )

        # 5) Predecir
        ingresos_futuros = modelo.predict(idx_futuro.reshape(-1, 1))

        # 6) Unir real + pronóstico
        tabla_real = diario[["fecha", "ingresos"]].copy()
        tabla_real["tipo"] = "Real"

        tabla_futura = pd.DataFrame({
            "fecha": fechas_futuras,
            "ingresos": ingresos_futuros,
            "tipo": "Pronóstico"
        })

        tabla_final = pd.concat([tabla_real, tabla_futura], ignore_index=True)

        return ResultadoPronostico(
            tabla=tabla_final,
            modelo=modelo
        )
