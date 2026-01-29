from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class ConfiguracionAplicacion:
    """
    Configuración central del proyecto.
    - Mantiene todo lo 'configurable' en un solo lugar.
    - Evita valores mágicos repartidos por el código.
    """

    # Identidad del proyecto
    nombre_aplicacion: str = "Dashboard BI - Ventas"
    version: str = "1.0.0"

    # Datos: ruta por defecto (cuando el usuario NO sube CSV)
    ruta_csv_por_defecto: Path = field(
        default_factory=lambda: Path("datos") / "ventas.csv"
    )

    # Formato de fechas (si necesitas validación estricta por formato)
    # Si es None, se intentará parsear automáticamente con pandas.
    formato_fecha: Optional[str] = None

    # Pronóstico
    horizonte_pronostico_dias: int = 30  # cuántos días hacia adelante predecir
    minimo_dias_historicos_para_pronostico: int = 14  # mínimo historial para pronóstico

    # Visualización
    cantidad_top_productos: int = 5

    # Calidad / rendimiento
    habilitar_cache: bool = True

    # Seguridad / límites (útil si luego lo expones como SaaS)
    max_filas_csv: int = 500_000  # límite recomendado para no romper memoria


    def ruta_csv_absoluta(self, raiz_proyecto: Optional[Path] = None) -> Path:
        """
        Devuelve la ruta absoluta del CSV por defecto.
        Si 'raiz_proyecto' es None, asume que se ejecuta desde la raíz del proyecto.
        """
        if raiz_proyecto is None:
            return self.ruta_csv_por_defecto.resolve()
        return (raiz_proyecto / self.ruta_csv_por_defecto).resolve()
