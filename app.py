import streamlit as st
import pandas as pd
import plotly.express as px
from nucleo.insights import GeneradorInsights
from nucleo.pronostico import PronosticadorVentasLineal

from nucleo.configuracion import ConfiguracionAplicacion
from nucleo.contratos import EsquemaDatosVentas
from nucleo.fuentes import FuenteDatosCSV, ErrorValidacionDatos, ErrorFuenteDatos
from nucleo.etl import LimpiadorDatos, TransformadorVentas
from nucleo.filtros import FiltroDatos, FiltroSeleccion, ComparadorPeriodos


# =========================
# CONFIGURACIÓN STREAMLIT
# =========================
st.set_page_config(
    page_title="Dashboard BI - Ventas",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard BI - Ventas (Filtros + Comparación de períodos)")


# =========================
# CONFIGURACIÓN DE NEGOCIO
# =========================
configuracion = ConfiguracionAplicacion()
esquema = EsquemaDatosVentas.esquema_por_defecto()


# =========================
# SIDEBAR: CARGA DE DATOS
# =========================
st.sidebar.header("Datos de entrada")

archivo_subido = st.sidebar.file_uploader(
    "Sube un CSV (opcional)",
    type=["csv"],
    help="Si no subes nada, se usará el CSV por defecto en datos/ventas.csv."
)


# =========================
# CARGA + VALIDACIÓN + NORMALIZACIÓN
# =========================
@st.cache_data
def cargar_datos(archivo):
    fuente = FuenteDatosCSV(
        configuracion=configuracion,
        esquema=esquema,
        archivo_subido=archivo
    )
    return fuente.cargar()


try:
    tabla_normalizada = cargar_datos(archivo_subido)
except ErrorValidacionDatos as e:
    st.error("❌ El archivo CSV no cumple el formato requerido.")
    st.write("Errores encontrados:")
    for err in e.errores:
        st.write(f"- {err}")
    st.stop()
except ErrorFuenteDatos as e:
    st.error("❌ Error cargando el CSV.")
    st.write(str(e))
    st.stop()


# =========================
# ETL: LIMPIEZA + TRANSFORMACIÓN
# =========================
limpiador = LimpiadorDatos()
tabla_limpia, resultado_limpieza = limpiador.limpiar(tabla_normalizada)

transformador = TransformadorVentas()
tabla_final = transformador.transformar(tabla_limpia)

# Advertencias de limpieza
if resultado_limpieza.advertencias:
    with st.expander("⚠️ Advertencias de limpieza"):
        for adv in resultado_limpieza.advertencias:
            st.write(f"- {adv}")


# =========================
# SIDEBAR: FILTROS
# =========================
st.sidebar.header("Filtros")

fecha_min = tabla_final["fecha"].min()
fecha_max = tabla_final["fecha"].max()

rango = st.sidebar.date_input(
    "Rango de fechas",
    value=(fecha_min, fecha_max),
    min_value=fecha_min,
    max_value=fecha_max
)
# Por seguridad: si el usuario selecciona solo una fecha
if isinstance(rango, tuple) and len(rango) == 2:
    fecha_inicio, fecha_fin = rango
else:
    fecha_inicio = rango
    fecha_fin = rango

region = st.sidebar.selectbox(
    "Región",
    options=["Todas"] + sorted(tabla_final["region"].dropna().unique().tolist())
)

canal = st.sidebar.selectbox(
    "Canal",
    options=["Todos"] + sorted(tabla_final["canal"].dropna().unique().tolist())
)

producto = st.sidebar.selectbox(
    "Producto",
    options=["Todos"] + sorted(tabla_final["id_producto"].dropna().unique().tolist())
)


# =========================
# APLICACIÓN DE FILTROS
# =========================
filtros = FiltroSeleccion(
    fecha_inicio=pd.to_datetime(fecha_inicio),
    fecha_fin=pd.to_datetime(fecha_fin),
    region=region,
    canal=canal,
    id_producto=producto
)

filtro_datos = FiltroDatos()
tabla_filtrada = filtro_datos.aplicar(tabla_final, filtros)


# =========================
# COMPARACIÓN DE PERÍODOS
# =========================
comparador = ComparadorPeriodos()
(_, periodo_anterior) = comparador.obtener_periodos(
    filtros.fecha_inicio,
    filtros.fecha_fin
)

tabla_anterior = filtro_datos.aplicar(
    tabla_final,
    FiltroSeleccion(
        fecha_inicio=periodo_anterior[0],
        fecha_fin=periodo_anterior[1],
        region=region,
        canal=canal,
        id_producto=producto
    )
)

# =========================
# KPIs (con comparación)
# =========================
def _comparar_kpi(columna: str) -> dict:
    actual = float(tabla_filtrada[columna].sum()) if not tabla_filtrada.empty else 0.0
    anterior = float(tabla_anterior[columna].sum()) if not tabla_anterior.empty else 0.0
    return comparador.comparar_metricas(actual, anterior)


comparacion_ingresos = _comparar_kpi("ingresos")
comparacion_margen = _comparar_kpi("margen")

clientes_activos = int(tabla_filtrada["id_cliente"].nunique()) if not tabla_filtrada.empty else 0
pedidos = int(tabla_filtrada["id_orden"].nunique()) if not tabla_filtrada.empty else 0

clientes_activos_anterior = int(tabla_anterior["id_cliente"].nunique()) if not tabla_anterior.empty else 0
pedidos_anterior = int(tabla_anterior["id_orden"].nunique()) if not tabla_anterior.empty else 0

comparacion_clientes = comparador.comparar_metricas(clientes_activos, clientes_activos_anterior)
comparacion_pedidos = comparador.comparar_metricas(pedidos, pedidos_anterior)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Ingresos",
        f"${comparacion_ingresos['actual']:,.2f}",
        delta=f"{comparacion_ingresos['variacion_pct']:.1f}%"
    )

with col2:
    st.metric(
        "Margen",
        f"${comparacion_margen['actual']:,.2f}",
        delta=f"{comparacion_margen['variacion_pct']:.1f}%"
    )

with col3:
    st.metric(
        "Clientes activos",
        f"{comparacion_clientes['actual']:.0f}",
        delta=f"{comparacion_clientes['variacion_pct']:.1f}%"
    )

with col4:
    st.metric(
        "Pedidos",
        f"{comparacion_pedidos['actual']:.0f}",
        delta=f"{comparacion_pedidos['variacion_pct']:.1f}%"
    )

st.markdown("---")

# =========================
# INSIGHTS (texto ejecutivo)
# =========================
st.subheader("🧠 Insights ejecutivos")

descripcion_filtros = f"(Región: {region}, Canal: {canal}, Producto: {producto})"

generador = GeneradorInsights()
insights = generador.generar(
    tabla_actual=tabla_filtrada,
    tabla_anterior=tabla_anterior,
    filtros_descripcion=descripcion_filtros
)

for ins in insights:
    if ins.tipo == "positivo":
        st.success(f"**{ins.titulo}** — {ins.mensaje}")
    elif ins.tipo == "negativo":
        st.error(f"**{ins.titulo}** — {ins.mensaje}")
    else:
        st.info(f"**{ins.titulo}** — {ins.mensaje}")

st.markdown("---")

# =========================
# GRÁFICOS (RESPETAN FILTROS)
# =========================
st.subheader("📈 Análisis visual (según filtros)")

if tabla_filtrada.empty:
    st.info("No hay datos para los filtros seleccionados.")
else:
    # ---- 1) Tendencia: ingresos y margen por día ----
    st.markdown("### Tendencia (Ingresos y Margen)")
    resumen_diario = (
        tabla_filtrada.groupby("fecha", as_index=False)
        .agg(ingresos=("ingresos", "sum"), margen=("margen", "sum"))
        .sort_values("fecha")
    )

    grafico_tendencia_ingresos = px.line(
        resumen_diario,
        x="fecha",
        y="ingresos",
        markers=True,
        title="Ingresos por día"
    )
    st.plotly_chart(grafico_tendencia_ingresos, use_container_width=True)

    grafico_tendencia_margen = px.line(
        resumen_diario,
        x="fecha",
        y="margen",
        markers=True,
        title="Margen por día"
    )
    st.plotly_chart(grafico_tendencia_margen, use_container_width=True)

    st.markdown("---")

    # ---- 2) Ingresos por región ----
    st.markdown("### Ingresos por región")
    resumen_region = (
        tabla_filtrada.groupby("region", as_index=False)
        .agg(ingresos=("ingresos", "sum"), margen=("margen", "sum"))
        .sort_values("ingresos", ascending=False)
    )

    grafico_region = px.bar(
        resumen_region,
        x="region",
        y="ingresos",
        title="Ingresos por región"
    )
    st.plotly_chart(grafico_region, use_container_width=True)

    st.markdown("---")

    # ---- 3) Ingresos por canal ----
    st.markdown("### Ingresos por canal")
    resumen_canal = (
        tabla_filtrada.groupby("canal", as_index=False)
        .agg(ingresos=("ingresos", "sum"), margen=("margen", "sum"))
        .sort_values("ingresos", ascending=False)
    )

    grafico_canal = px.bar(
        resumen_canal,
        x="canal",
        y="ingresos",
        title="Ingresos por canal"
    )
    st.plotly_chart(grafico_canal, use_container_width=True)

    st.markdown("---")

    # ---- 4) Top productos ----
    st.markdown("### Top productos (Ingresos y Margen)")
    top_productos = (
        tabla_filtrada.groupby("id_producto", as_index=False)
        .agg(
            ingresos=("ingresos", "sum"),
            margen=("margen", "sum"),
            cantidad_total=("cantidad", "sum"),
            pedidos=("id_orden", "nunique")
        )
        .sort_values("ingresos", ascending=False)
        .head(configuracion.cantidad_top_productos)
    )

    colA, colB = st.columns((1, 2))

    with colA:
        st.dataframe(top_productos)

    with colB:
        grafico_top_productos = px.bar(
            top_productos,
            x="id_producto",
            y="ingresos",
            title=f"Top {configuracion.cantidad_top_productos} productos por ingresos"
        )
        st.plotly_chart(grafico_top_productos, use_container_width=True)

    st.markdown("---")

    # ---- 5) (Opcional útil) Tabla resumen para exportar ----
    with st.expander("📄 Resumen para exportar"):
        st.dataframe(resumen_diario)
        csv = resumen_diario.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descargar resumen diario (CSV)",
            data=csv,
            file_name="resumen_diario.csv",
            mime="text/csv"
        )

# =========================
# PRONÓSTICO DE INGRESOS
# =========================
st.subheader("🔮 Pronóstico de ingresos")

if tabla_filtrada.empty:
    st.info("No hay datos suficientes para generar pronóstico.")
else:
    dias_pronostico = st.slider(
        "Días a pronosticar",
        min_value=7,
        max_value=90,
        value=30,
        step=7
    )

    try:
        pronosticador = PronosticadorVentasLineal()
        resultado = pronosticador.entrenar_y_pronosticar(
            tabla_filtrada,
            dias_futuros=dias_pronostico
        )

        import plotly.express as px

        grafico_pronostico = px.line(
            resultado.tabla,
            x="fecha",
            y="ingresos",
            color="tipo",
            markers=True,
            title="Ingresos reales vs pronosticados"
        )

        st.plotly_chart(grafico_pronostico, use_container_width=True)

        st.caption(
            "El pronóstico se basa en una regresión lineal simple sobre los ingresos diarios. "
            "Asume que la tendencia histórica continúa."
        )

    except Exception as e:
        st.error("No se pudo generar el pronóstico.")
        st.write(str(e))

# =========================
# INFO DE PERÍODOS (para transparencia)
# =========================
with st.expander("📅 Detalle de comparación de períodos"):
    st.write(f"**Período actual:** {filtros.fecha_inicio.date()} → {filtros.fecha_fin.date()}")
    st.write(f"**Período anterior:** {periodo_anterior[0].date()} → {periodo_anterior[1].date()}")


# =========================
# TABLAS (debug/entendimiento)
# =========================
st.subheader("Vista de datos filtrados")
st.dataframe(tabla_filtrada)

st.subheader("Vista de datos del período anterior (para comparación)")
st.dataframe(tabla_anterior)
