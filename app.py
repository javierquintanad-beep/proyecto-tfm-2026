import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from io import StringIO

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor de Temperatura — TFM 2026",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── URL del dataset en GitHub ────────────────────────────────────────────────
CSV_URL = "https://raw.githubusercontent.com/javierquintanad-beep/proyecto-tfm-2026/main/temperature_batch_20260623_021527.csv"

# ── Estilos CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1e2130, #262b40);
    border: 1px solid #3a3f5c;
    border-radius: 12px;
    padding: 16px 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
div[data-testid="metric-container"] label {
    color: #8b92b8 !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e8eaf6 !important;
    font-size: 1.8rem !important;
    font-weight: 700;
}
.header-box {
    background: linear-gradient(135deg, #1a1f35, #252b45);
    border-left: 4px solid #5c6bc0;
    border-radius: 10px;
    padding: 20px 28px;
    margin-bottom: 24px;
}
.header-box h1 { color: #e8eaf6; margin: 0; font-size: 1.7rem; font-weight: 700; }
.header-box p  { color: #8b92b8; margin: 4px 0 0; font-size: 0.9rem; }
.section-title {
    color: #9fa8da;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border-bottom: 1px solid #3a3f5c;
    padding-bottom: 6px;
    margin: 28px 0 16px;
}
</style>
""", unsafe_allow_html=True)

# ── Colores ──────────────────────────────────────────────────────────────────
SENSOR_COLORS = {
    "Temperatura 01": "#ef5350", "Temperatura 02": "#ffa726",
    "Temperatura 03": "#ff7043", "Temperatura 04": "#ffca28",
    "Temperatura 05": "#ec407a", "Temperatura 06": "#ab47bc",
    "Temperatura 07": "#26c6da", "Temperatura 08": "#29b6f6",
    "Temperatura 09": "#66bb6a", "Temperatura 10": "#26a69a",
    "Temperatura 11": "#7e57c2", "Temperatura 12": "#d4e157",
}
ZONA_COLORS = {
    "Alta (>50°C)":    "#ef5350",
    "Media (35–50°C)": "#ffa726",
    "Baja (15–35°C)":  "#42a5f5",
    "Fría (<15°C)":    "#29b6f6",
}

# ── Carga de datos ───────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    resp = requests.get(CSV_URL, timeout=15)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    for col in ["sampled_at", "observed_at", "generated_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    df["value_celsius"] = pd.to_numeric(df["value_celsius"], errors="coerce")
    df = df.dropna(subset=["value_celsius", "sampled_at"])
    df = df.sort_values("sampled_at").reset_index(drop=True)
    def classify(t):
        if t >= 50:   return "Alta (>50°C)"
        elif t >= 35: return "Media (35–50°C)"
        elif t >= 15: return "Baja (15–35°C)"
        else:         return "Fría (<15°C)"
    df["zona"] = df["value_celsius"].apply(classify)
    df["tiempo_label"] = df["sampled_at"].dt.strftime("%H:%M:%S")
    return df

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")
    st.divider()
    if st.button("🔄 Recargar datos", use_container_width=True):
        st.cache_data.clear()
    st.divider()
    st.markdown("### 🎛️ Filtros")
    umbral_alerta  = st.slider("Umbral de alerta (°C)",  30, 70, 55, 1)
    umbral_critico = st.slider("Umbral crítico (°C)",    40, 80, 60, 1)
    st.divider()
    st.markdown("""
    <small style='color:#8b92b8'>
    📡 Datos muestreados cada 30 s<br>
    🌡️ 12 sensores monitoreados<br>
    📅 Batch: 2026-06-23<br>
    👤 javierquintanad-beep
    </small>
    """, unsafe_allow_html=True)

# ── Encabezado ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-box">
  <h1>🌡️ Monitor de Temperatura — Sistema IoT</h1>
  <p>Análisis de 12 sensores distribuidos · Muestreo cada 30 segundos · TFM 2026</p>
</div>
""", unsafe_allow_html=True)

# ── Cargar datos ─────────────────────────────────────────────────────────────
with st.spinner("Cargando datos desde GitHub..."):
    try:
        df = load_data()
    except Exception as e:
        st.error(f"❌ Error al cargar el dataset: {e}")
        st.stop()

# ── Estadísticas ─────────────────────────────────────────────────────────────
stats = df.groupby("name")["value_celsius"].agg(
    Promedio="mean", Mínimo="min", Máximo="max",
    Desv_Std="std", Último="last"
).round(2).reset_index().rename(columns={"name": "Sensor"})
stats["Rango"]  = (stats["Máximo"] - stats["Mínimo"]).round(2)
stats["Zona"]   = stats["Promedio"].apply(
    lambda t: "Alta (>50°C)" if t >= 50 else "Media (35–50°C)" if t >= 35
    else "Baja (15–35°C)" if t >= 15 else "Fría (<15°C)"
)
stats["Alerta"] = stats["Máximo"].apply(
    lambda v: "🔴 Crítico" if v >= umbral_critico
    else "🟠 Alerta" if v >= umbral_alerta else "🟢 Normal"
)
stats["Tendencia"] = (
    stats["Último"] - stats["Promedio"]
).round(2)
ultimo_registro = df["sampled_at"].max()
n_sensores      = df["name"].nunique()
n_muestras      = df["sample_number"].nunique()
temp_max        = df["value_celsius"].max()
temp_min        = df["value_celsius"].min()
temp_avg        = df["value_celsius"].mean()
sensores_alerta = (stats["Máximo"] >= umbral_alerta).sum()

# ── KPIs ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Indicadores Clave</div>', unsafe_allow_html=True)
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Sensores activos",   n_sensores)
k2.metric("Muestras totales",   n_muestras)
k3.metric("Temp. máxima",       f"{temp_max:.1f} °C")
k4.metric("Temp. mínima",       f"{temp_min:.1f} °C")
k5.metric("Temp. promedio",     f"{temp_avg:.1f} °C")
k6.metric("Sensores en alerta", sensores_alerta,
          delta=f"umbral {umbral_alerta}°C", delta_color="inverse")

# ── Serie temporal ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📈 Serie Temporal por Sensor</div>', unsafe_allow_html=True)
sensores_sel = st.multiselect(
    "Filtrar sensores",
    options=sorted(df["name"].unique()),
    default=sorted(df["name"].unique()),
    key="multi_sensor"
)
df_f = df[df["name"].isin(sensores_sel)]
fig_line = go.Figure()
for sensor in sensores_sel:
    d = df_f[df_f["name"] == sensor].sort_values("sampled_at")
    fig_line.add_trace(go.Scatter(
        x=d["sampled_at"], y=d["value_celsius"],
        mode="lines+markers", name=sensor,
        line=dict(width=2, color=SENSOR_COLORS.get(sensor, "#aaa")),
        marker=dict(size=5),
        hovertemplate=f"<b>{sensor}</b><br>%{{x|%H:%M:%S}}<br>%{{y:.1f}} °C<extra></extra>"
    ))
fig_line.add_hline(y=umbral_alerta,  line_dash="dash", line_color="#ffa726",
                   annotation_text=f"Alerta ({umbral_alerta}°C)",   annotation_position="top right")
fig_line.add_hline(y=umbral_critico, line_dash="dash", line_color="#ef5350",
                   annotation_text=f"Crítico ({umbral_critico}°C)", annotation_position="top right")
fig_line.update_layout(
    template="plotly_dark", paper_bgcolor="#1a1f35", plot_bgcolor="#1e2130",
    height=420, hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(title="Hora de muestreo", gridcolor="#2d3250"),
    yaxis=dict(title="Temperatura (°C)", gridcolor="#2d3250"),
    margin=dict(l=40, r=40, t=40, b=40),
)
st.plotly_chart(fig_line, use_container_width=True)
# ── Estado general + Histograma ──────────────────────────────────────────────
st.markdown(
    '<div class="section-title">🎯 Estado General del Sistema</div>',
    unsafe_allow_html=True
)

col_gauge, col_hist = st.columns([1, 2])

with col_gauge:

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=temp_max,
        number={"suffix": " °C"},
        title={"text": "Temperatura Máxima"},
        gauge={
            "axis": {"range": [0, 80]},
            "bar": {"color": "#ef5350"},
            "steps": [
                {"range": [0, 15], "color": "#29b6f6"},
                {"range": [15, 35], "color": "#42a5f5"},
                {"range": [35, 50], "color": "#ffa726"},
                {"range": [50, 80], "color": "#ef5350"}
            ],
            "threshold": {
                "line": {"color": "#ffffff", "width": 4},
                "value": umbral_alerta
            }
        }
    ))

    fig_gauge.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1a1f35",
        height=350,
        margin=dict(l=20,r=20,t=40,b=20)
    )

    st.plotly_chart(fig_gauge, use_container_width=True)

with col_hist:

    fig_hist = px.histogram(
        df,
        x="value_celsius",
        nbins=25,
        template="plotly_dark"
    )

    fig_hist.update_traces(
        marker_color="#5c6bc0"
    )

    fig_hist.update_layout(
        paper_bgcolor="#1a1f35",
        plot_bgcolor="#1e2130",
        height=350,
        title=dict(
            text="Distribución global de temperaturas",
            font=dict(size=13, color="#9fa8da")
        ),
        xaxis=dict(
            title="Temperatura (°C)",
            gridcolor="#2d3250"
        ),
        yaxis=dict(
            title="Frecuencia",
            gridcolor="#2d3250"
        )
    )

    st.plotly_chart(fig_hist, use_container_width=True)
st.markdown(
    '<div class="section-title">🔥 Top 5 Sensores Más Calientes</div>',
    unsafe_allow_html=True
)

top5 = (
    stats
    .sort_values("Máximo", ascending=False)
    .head(5)
)

fig_top = go.Figure()

fig_top.add_trace(go.Bar(
    x=top5["Máximo"],
    y=top5["Sensor"],
    orientation="h",
    marker_color="#ef5350",
    hovertemplate="<b>%{y}</b><br>%{x:.1f} °C<extra></extra>"
))

fig_top.update_layout(
    template="plotly_dark",
    paper_bgcolor="#1a1f35",
    plot_bgcolor="#1e2130",
    height=320,
    title=dict(
        text="Top 5 temperaturas máximas registradas",
        font=dict(size=13, color="#9fa8da")
    ),
    xaxis=dict(
        title="°C",
        gridcolor="#2d3250"
    ),
    yaxis=dict(
        title=""
    )
)

st.plotly_chart(fig_top, use_container_width=True)

# ── Boxplot + Heatmap ────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📦 Distribución y Mapa de Calor</div>', unsafe_allow_html=True)
col_box, col_heat = st.columns(2)

with col_box:
    fig_box = go.Figure()
    for sensor in sorted(df["name"].unique()):
        fig_box.add_trace(go.Box(
            y=df[df["name"] == sensor]["value_celsius"],
            name=sensor, marker_color=SENSOR_COLORS.get(sensor, "#aaa"),
            boxmean="sd",
            hovertemplate=f"<b>{sensor}</b><br>%{{y:.1f}} °C<extra></extra>"
        ))
    fig_box.update_layout(
        template="plotly_dark", paper_bgcolor="#1a1f35", plot_bgcolor="#1e2130",
        height=400, showlegend=False,
        title=dict(text="Distribución por sensor (boxplot)", font=dict(size=13, color="#9fa8da")),
        xaxis=dict(tickangle=-45, gridcolor="#2d3250"),
        yaxis=dict(title="Temperatura (°C)", gridcolor="#2d3250"),
        margin=dict(l=40, r=20, t=50, b=80),
    )
    st.plotly_chart(fig_box, use_container_width=True)

with col_heat:
    pivot = df.pivot_table(index="name", columns="sample_number",
                           values="value_celsius", aggfunc="mean")
    fig_heat = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"M{c}" for c in pivot.columns],
        y=pivot.index.tolist(),
        colorscale="RdYlBu_r",
        hovertemplate="Sensor: %{y}<br>Muestra: %{x}<br>%{z:.1f} °C<extra></extra>",
        colorbar=dict(
    title=dict(
        text="°C",
        font=dict(color="#9fa8da")
    ),
    tickfont=dict(color="#9fa8da")
)

    ))
    fig_heat.update_layout(
        template="plotly_dark", paper_bgcolor="#1a1f35", plot_bgcolor="#1e2130",
        height=400,
        title=dict(text="Mapa de calor — temperatura por muestra", font=dict(size=13, color="#9fa8da")),
        xaxis=dict(title="Muestra", tickangle=-45, gridcolor="#2d3250"),
        yaxis=dict(title=""),
        margin=dict(l=10, r=20, t=50, b=80),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ── Radar + Barras ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🔬 Comparativa entre Sensores</div>', unsafe_allow_html=True)
col_radar, col_bar = st.columns(2)

with col_radar:
    cats = stats["Sensor"].tolist()
    vals = stats["Promedio"].tolist()
    fig_radar = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=cats + [cats[0]],
        fill="toself", line_color="#5c6bc0",
        fillcolor="rgba(92,107,192,0.25)",
        hovertemplate="%{theta}: %{r:.1f} °C<extra></extra>"
    ))
    fig_radar.update_layout(
        template="plotly_dark", paper_bgcolor="#1a1f35", plot_bgcolor="#1a1f35",
        height=380, showlegend=False,
        polar=dict(
            bgcolor="#1e2130",
            radialaxis=dict(visible=True, gridcolor="#2d3250", color="#8b92b8"),
            angularaxis=dict(gridcolor="#2d3250", color="#8b92b8")
        ),
        title=dict(text="Temperatura promedio — radar", font=dict(size=13, color="#9fa8da")),
        margin=dict(l=40, r=40, t=50, b=40),
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with col_bar:
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=stats["Sensor"], y=stats["Promedio"],
        marker_color=[SENSOR_COLORS.get(s, "#aaa") for s in stats["Sensor"]],
        error_y=dict(type="data", array=stats["Desv_Std"].tolist(), visible=True, color="#8b92b8"),
        hovertemplate="<b>%{x}</b><br>Promedio: %{y:.2f} °C<extra></extra>"
    ))
    fig_bar.add_hline(y=umbral_alerta, line_dash="dash", line_color="#ffa726")
    fig_bar.update_layout(
        template="plotly_dark", paper_bgcolor="#1a1f35", plot_bgcolor="#1e2130",
        height=380, showlegend=False, bargap=0.3,
        title=dict(text="Temperatura promedio ± desv. estándar", font=dict(size=13, color="#9fa8da")),
        xaxis=dict(tickangle=-45, gridcolor="#2d3250"),
        yaxis=dict(title="°C", gridcolor="#2d3250"),
        margin=dict(l=40, r=20, t=50, b=80),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── Zonas térmicas ───────────────────────────────────────────────────────────
st.markdown('<div class="section-title">🗂️ Clasificación por Zona Térmica</div>', unsafe_allow_html=True)
col_pie, col_zona = st.columns([1, 2])

with col_pie:
    zona_counts = df["zona"].value_counts().reset_index()
    zona_counts.columns = ["Zona", "Registros"]
    fig_pie = go.Figure(go.Pie(
        labels=zona_counts["Zona"],
        values=zona_counts["Registros"],
        marker_colors=[ZONA_COLORS.get(z, "#aaa") for z in zona_counts["Zona"]],
        hole=0.45, textinfo="label+percent",
        hovertemplate="%{label}: %{value} registros (%{percent})<extra></extra>"
    ))
    fig_pie.update_layout(
        template="plotly_dark", paper_bgcolor="#1a1f35", height=340,
        title=dict(text="Registros por zona térmica", font=dict(size=13, color="#9fa8da")),
        legend=dict(font=dict(color="#9fa8da")),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_zona:
    zona_sensor = df.groupby(["name", "zona"])["value_celsius"].count().reset_index()
    zona_sensor.columns = ["Sensor", "Zona", "Registros"]
    fig_zona = px.bar(
        zona_sensor, x="Sensor", y="Registros", color="Zona",
        color_discrete_map=ZONA_COLORS, barmode="stack", template="plotly_dark",
    )
    fig_zona.update_layout(
        paper_bgcolor="#1a1f35", plot_bgcolor="#1e2130", height=340,
        title=dict(text="Registros por zona y sensor", font=dict(size=13, color="#9fa8da")),
        xaxis=dict(tickangle=-45, gridcolor="#2d3250"),
        yaxis=dict(gridcolor="#2d3250"),
        legend=dict(font=dict(color="#9fa8da")),
        margin=dict(l=40, r=20, t=50, b=80),
    )
    st.plotly_chart(fig_zona, use_container_width=True)
st.markdown(
    '<div class="section-title">📈 Tendencia por Sensor</div>',
    unsafe_allow_html=True
)

fig_trend = go.Figure()


fig_trend.add_trace(go.Bar(
    x=stats["Sensor"],
    y=stats["Tendencia"],
    marker_color=[
        "#66bb6a" if v >= 0 else "#ef5350"
        for v in stats["Tendencia"]
    ],
    hovertemplate="<b>%{x}</b><br>%{y:.2f} °C<extra></extra>"
))

fig_trend.update_layout(
    template="plotly_dark",
    paper_bgcolor="#1a1f35",
    plot_bgcolor="#1e2130",
    height=340,
    title=dict(
        text="Diferencia entre último valor y promedio",
        font=dict(size=13, color="#9fa8da")
    ),
    xaxis=dict(
        tickangle=-45,
        gridcolor="#2d3250"
    ),
    yaxis=dict(
        title="Δ °C",
        gridcolor="#2d3250"
    )
)

st.plotly_chart(fig_trend, use_container_width=True)
# ── Tabla estadística ─────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📋 Tabla de Estadísticas por Sensor</div>', unsafe_allow_html=True)

tabla = stats.rename(columns={
    "Promedio": "Promedio (°C)", "Mínimo": "Mín (°C)", "Máximo": "Máx (°C)",
    "Desv_Std": "Desv. Std", "Último": "Último (°C)", "Rango": "Rango (°C)",
}).set_index("Sensor")

def color_alerta(val):
    if "Crítico" in str(val): return "color: #ef5350; font-weight:bold"
    if "Alerta"  in str(val): return "color: #ffa726; font-weight:bold"
    return "color: #66bb6a"

def color_temp(val):
    try:
        v = float(val)
        if v >= 50: return "color: #ef5350"
        if v >= 35: return "color: #ffa726"
        if v >= 15: return "color: #42a5f5"
        return "color: #29b6f6"
    except: return ""

styled = (tabla.style
    .applymap(color_alerta, subset=["Alerta"])
    .applymap(color_temp,   subset=["Promedio (°C)", "Máx (°C)", "Mín (°C)", "Último (°C)"])
    .format({
        "Promedio (°C)": "{:.2f}", "Mín (°C)": "{:.2f}", "Máx (°C)": "{:.2f}",
        "Desv. Std": "{:.3f}", "Último (°C)": "{:.2f}", "Rango (°C)": "{:.2f}",
    })
    .set_table_styles([
        {"selector": "th", "props": [("background-color", "#262b40"), ("color", "#9fa8da"),
                                      ("font-size", "0.78rem"), ("text-transform", "uppercase")]},
        {"selector": "td", "props": [("background-color", "#1e2130"), ("color", "#e8eaf6"),
                                      ("border-bottom", "1px solid #2d3250")]},
    ])
)
st.dataframe(styled, use_container_width=True, height=420)

# ── Datos crudos ──────────────────────────────────────────────────────────────
with st.expander("🔎 Ver datos crudos"):
    cols_show = ["sampled_at", "name", "value_celsius", "zona", "sample_number"]
    st.dataframe(
        df[cols_show].rename(columns={
            "sampled_at": "Fecha/Hora", "name": "Sensor",
            "value_celsius": "Temp (°C)", "zona": "Zona", "sample_number": "Muestra"
        }).sort_values("Fecha/Hora", ascending=False),
        use_container_width=True, height=300
    )
    st.download_button(
        "⬇️ Descargar CSV filtrado",
        df[cols_show].to_csv(index=False).encode("utf-8"),
        "temperaturas_filtrado.csv", "text/csv"
    )

# ── Footer ────────────────────────────────────────────────────────────────────
ts = ultimo_registro.strftime("%Y-%m-%d %H:%M:%S UTC") if pd.notna(ultimo_registro) else "N/A"
st.markdown(f"""
<div style='text-align:center;color:#3a3f5c;font-size:0.75rem;margin-top:40px;
            border-top:1px solid #2d3250;padding-top:16px;'>
    Monitor de Temperatura IoT · TFM 2026 · Último batch: {ts} · {n_sensores} sensores · {n_muestras} muestras
</div>
""", unsafe_allow_html=True)