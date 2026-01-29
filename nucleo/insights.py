from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


@dataclass
class Insight:
    titulo: str
    mensaje: str
    tipo: str  # "positivo" | "negativo" | "neutral"


class GeneradorInsights:
    """
    Genera insights ejecutivos a partir de:
    - tabla filtrada (periodo actual)
    - tabla del periodo anterior
    """

    def generar(
        self,
        tabla_actual: pd.DataFrame,
        tabla_anterior: pd.DataFrame,
        filtros_descripcion: str = ""
    ) -> List[Insight]:

        insights: List[Insight] = []

        # Si no hay datos, devolver insight neutral
        if tabla_actual.empty:
            return [
                Insight(
                    titulo="Sin datos",
                    mensaje="No hay registros para los filtros seleccionados. Ajusta el rango de fechas o filtros.",
                    tipo="neutral",
                )
            ]

        # ---- 1) Ingresos y variación vs periodo anterior ----
        ingresos_actual = float(tabla_actual["ingresos"].sum())
        ingresos_anterior = float(tabla_anterior["ingresos"].sum()) if not tabla_anterior.empty else 0.0

        variacion_pct = 0.0
        if ingresos_anterior != 0:
            variacion_pct = ((ingresos_actual - ingresos_anterior) / ingresos_anterior) * 100

        if ingresos_anterior == 0 and ingresos_actual > 0:
            insights.append(
                Insight(
                    titulo="Ingresos sin referencia histórica",
                    mensaje="Hay ingresos en el período actual, pero el período anterior no tiene datos comparables. "
                            "Esto puede ocurrir por filtros muy específicos o falta de historial.",
                    tipo="neutral",
                )
            )
        else:
            tipo = "neutral"
            if variacion_pct > 0:
                tipo = "positivo"
            elif variacion_pct < 0:
                tipo = "negativo"

            insights.append(
                Insight(
                    titulo="Rendimiento vs período anterior",
                    mensaje=f"Los ingresos del período actual son ${ingresos_actual:,.2f} "
                            f"({variacion_pct:+.1f}% vs el período anterior). {filtros_descripcion}".strip(),
                    tipo=tipo,
                )
            )

        # ---- 2) Región que más aporta ingresos ----
        if "region" in tabla_actual.columns and tabla_actual["region"].notna().any():
            por_region = (
                tabla_actual.groupby("region", as_index=False)
                .agg(ingresos=("ingresos", "sum"), margen=("margen", "sum"))
                .sort_values("ingresos", ascending=False)
            )
            top_region = por_region.iloc[0]
            total_ing = por_region["ingresos"].sum()
            aporte_pct = (top_region["ingresos"] / total_ing) * 100 if total_ing > 0 else 0.0

            insights.append(
                Insight(
                    titulo="Región líder",
                    mensaje=f"La región con más ingresos es **{top_region['region']}**, aportando "
                            f"{aporte_pct:.1f}% de los ingresos (${top_region['ingresos']:,.2f}).",
                    tipo="positivo",
                )
            )

        # ---- 3) Canal con mejor rendimiento ----
        if "canal" in tabla_actual.columns and tabla_actual["canal"].notna().any():
            por_canal = (
                tabla_actual.groupby("canal", as_index=False)
                .agg(ingresos=("ingresos", "sum"), margen=("margen", "sum"))
                .sort_values("ingresos", ascending=False)
            )
            top_canal = por_canal.iloc[0]
            insights.append(
                Insight(
                    titulo="Canal más fuerte",
                    mensaje=f"El canal con mayor ingreso es **{top_canal['canal']}** con "
                            f"${top_canal['ingresos']:,.2f}.",
                    tipo="neutral",
                )
            )

        # ---- 4) Producto líder por ingresos y alerta por margen bajo ----
        por_producto = (
            tabla_actual.groupby("id_producto", as_index=False)
            .agg(
                ingresos=("ingresos", "sum"),
                margen=("margen", "sum"),
                cantidad=("cantidad", "sum")
            )
            .sort_values("ingresos", ascending=False)
        )

        if not por_producto.empty:
            top_prod = por_producto.iloc[0]
            margen_pct = (top_prod["margen"] / top_prod["ingresos"] * 100) if top_prod["ingresos"] > 0 else 0.0

            tipo_prod = "positivo"
            if margen_pct < 15:  # umbral simple
                tipo_prod = "negativo"

            insights.append(
                Insight(
                    titulo="Producto líder y rentabilidad",
                    mensaje=f"El producto con más ingresos es **{top_prod['id_producto']}** "
                            f"(${top_prod['ingresos']:,.2f}). Su margen estimado es {margen_pct:.1f}%.",
                    tipo=tipo_prod,
                )
            )

        # ---- 5) Concentración (riesgo): dependencia de 1 producto ----
        if not por_producto.empty:
            total_ingresos = por_producto["ingresos"].sum()
            share_top = (por_producto.iloc[0]["ingresos"] / total_ingresos) * 100 if total_ingresos > 0 else 0.0
            if share_top >= 60:
                insights.append(
                    Insight(
                        titulo="Riesgo de concentración",
                        mensaje=f"Más del {share_top:.1f}% de los ingresos provienen de un solo producto "
                                f"(**{por_producto.iloc[0]['id_producto']}**). Considera diversificar.",
                        tipo="negativo",
                    )
                )

        return insights
