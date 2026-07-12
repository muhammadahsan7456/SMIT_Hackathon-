"""
Smart City AQI Dashboard
========================
Single-file production dashboard: dashboard/app.py

Required libraries (install once):
    pip install streamlit pandas plotly snowflake-connector-python streamlit-autorefresh reportlab kaleido

Notes:
- Uses existing config.py (SNOWFLAKE_CONFIG) — unchanged.
- Reads exclusively from Gold-layer VIEWS (no raw table queries):
      GOLD.VW_CITY_AQI_SUMMARY
      GOLD.VW_LATEST_SENSOR
      GOLD.VW_SENSOR_HISTORY
      GOLD.VW_AQI_STATUS
      GOLD.VW_POLLUTANT_SUMMARY
- Every DB call is wrapped in try/except so a missing view, a dropped
  connection, or an empty result never crashes the app — it degrades
  gracefully with an inline banner instead.
"""

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import snowflake.connector
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config import SNOWFLAKE_CONFIG

# =====================================================================
# PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="Smart City AQI Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st_autorefresh(interval=10000, key="refresh")

# =====================================================================
# GLOBAL CSS — dark theme, glassmorphism, gradients, hover effects
# =====================================================================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        .stApp {
            background: radial-gradient(circle at 15% 0%, #16233b 0%, #0b0f19 45%, #090c14 100%);
        }

        /* ---------- Hero banner ---------- */
        .hero-banner {
            background: linear-gradient(120deg, #1e3a5f 0%, #2d5f8a 45%, #1e5f74 100%);
            padding: 2rem 2.5rem;
            border-radius: 20px;
            margin-bottom: 1.4rem;
            box-shadow: 0 10px 35px rgba(0,0,0,0.4);
            border: 1px solid rgba(255,255,255,0.08);
            position: relative;
            overflow: hidden;
        }
        .hero-title { font-size: 2.2rem; font-weight: 900; color: #fff; margin: 0; letter-spacing: -0.5px; }
        .hero-subtitle { font-size: 1rem; color: #bcd7ea; margin-top: 0.35rem; font-weight: 400; }
        .live-pill {
            display: inline-flex; align-items: center; gap: 6px;
            background: rgba(46,204,113,0.15); border: 1px solid rgba(46,204,113,0.45);
            color: #2ecc71; padding: 4px 12px; border-radius: 20px;
            font-size: 0.78rem; font-weight: 700; margin-top: 0.9rem;
        }
        .live-dot { width: 8px; height: 8px; background: #2ecc71; border-radius: 50%; animation: pulse 1.5s infinite; }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(46,204,113,0.6); }
            70% { box-shadow: 0 0 0 9px rgba(46,204,113,0); }
            100% { box-shadow: 0 0 0 0 rgba(46,204,113,0); }
        }

        /* ---------- Glass KPI cards ---------- */
        .kpi-card {
            background: rgba(255,255,255,0.045);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 18px;
            padding: 1.1rem 1.3rem;
            transition: transform 0.2s ease, border 0.2s ease, box-shadow 0.2s ease;
            height: 100%;
        }
        .kpi-card:hover {
            transform: translateY(-4px);
            border: 1px solid rgba(46,204,113,0.5);
            box-shadow: 0 8px 25px rgba(46,204,113,0.12);
        }
        .kpi-label { font-size: 0.74rem; color: #93a3b8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; }
        .kpi-value { font-size: 1.7rem; font-weight: 900; color: #fff; margin-top: 0.25rem; }
        .kpi-icon { font-size: 1.4rem; margin-bottom: 0.3rem; }

        /* ---------- Section headers ---------- */
        .section-header {
            color: #fff; font-weight: 800; font-size: 1.25rem;
            margin-top: 0.6rem; margin-bottom: 0.8rem;
            border-left: 4px solid #2ecc71; padding-left: 12px;
        }

        /* ---------- Alerts / status badges ---------- */
        .alert-banner { padding: 0.9rem 1.3rem; border-radius: 12px; font-weight: 700; font-size: 1.0rem; margin-bottom: 0.8rem; }
        .status-chip {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 0.55rem 1rem; border-radius: 12px; font-weight: 700; font-size: 0.85rem;
            margin: 4px 6px 4px 0; border: 1px solid rgba(255,255,255,0.08);
        }

        [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

        [data-testid="stSidebar"] {
            background: #0a0e18;
            border-right: 1px solid rgba(255,255,255,0.06);
        }

        .footer-box {
            text-align: center; padding: 1.4rem 0 0.6rem 0;
            color: #6b7a90; font-size: 0.82rem; border-top: 1px solid rgba(255,255,255,0.06); margin-top: 1.5rem;
        }
        .footer-box b { color: #93a3b8; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================================
# COLOR / CLASSIFICATION HELPERS
# =====================================================================
def aqi_color_fine(aqi_val):
    """Fine-grained 6-tier classification — used for live alerts & charts."""
    if aqi_val is None or pd.isna(aqi_val):
        return "#7f8c8d", "Unknown"
    if aqi_val <= 50:
        return "#2ecc71", "Good"
    elif aqi_val <= 100:
        return "#f1c40f", "Moderate"
    elif aqi_val <= 150:
        return "#e67e22", "Unhealthy for Sensitive Groups"
    elif aqi_val <= 200:
        return "#e74c3c", "Unhealthy"
    elif aqi_val <= 300:
        return "#9b59b6", "Very Unhealthy"
    else:
        return "#6e2c00", "Hazardous"


def aqi_zone_4(aqi_val):
    """4-zone classification for gauge / status cards, per spec: 0-50 / 51-100 / 101-200 / 201-500."""
    if aqi_val is None or pd.isna(aqi_val):
        return "#7f8c8d", "Unknown"
    if aqi_val <= 50:
        return "#2ecc71", "Good"
    elif aqi_val <= 100:
        return "#f1c40f", "Moderate"
    elif aqi_val <= 200:
        return "#e67e22", "Unhealthy"
    else:
        return "#e74c3c", "Hazardous"


def find_col(df, candidates):
    """Return first matching column name (case-insensitive) present in df, else None."""
    cols_upper = {c.upper(): c for c in df.columns}
    for cand in candidates:
        if cand.upper() in cols_upper:
            return cols_upper[cand.upper()]
    return None


def kpi_card(icon, label, value, col):
    with col:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-icon">{icon}</div>
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =====================================================================
# SNOWFLAKE CONNECTION
# =====================================================================
def get_connection():
    return snowflake.connector.connect(
        user=SNOWFLAKE_CONFIG["user"],
        password=SNOWFLAKE_CONFIG["password"],
        account=SNOWFLAKE_CONFIG["account"],
        warehouse=SNOWFLAKE_CONFIG["warehouse"],
        database=SNOWFLAKE_CONFIG["database"],
        schema="GOLD",
        role=SNOWFLAKE_CONFIG["role"],
    )


def run_query(query, error_key):
    """Execute query safely and return DataFrame."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(query)

        df = cursor.fetch_pandas_all()

        cursor.close()
        conn.close()

        if not df.empty:
            df.columns = [c.upper() for c in df.columns]

        return df, None

    except Exception as e:
        print(f"🔴 Query Error ({error_key}): {str(e)}")
        return pd.DataFrame(), str(e)
    """Generic safe query runner — never raises, always returns a DataFrame."""
    try:
        conn = get_connection()
        conn.cursor().execute("ALTER SESSION SET QUERY_TAG = 'dashboard'")
        df = pd.read_sql(query, conn, timeout_seconds=30)
        conn.close()
        df.columns = [c.upper() for c in df.columns]
        return df, None
    except Exception as e:
        error_msg = str(e)
        print(f"🔴 Query Error ({error_key}): {error_msg}")
        return pd.DataFrame(), error_msg


# =====================================================================
# DATA LOADERS — one per Gold view, all cached + error safe
# =====================================================================
@st.cache_data(ttl=30, show_spinner=False)
def load_summary():
    with st.spinner("📊 Loading AQI Summary..."):
        return run_query("""
            SELECT *
            FROM GOLD.VW_CITY_AQI_SUMMARY
            ORDER BY AVG_AQI DESC
        """, "summary")


@st.cache_data(ttl=10, show_spinner=False)
def load_latest_sensor():
    with st.spinner("🔄 Loading Latest Sensor Data..."):
        return run_query("SELECT * FROM GOLD.VW_LATEST_SENSOR LIMIT 1000", "latest_sensor")


@st.cache_data(ttl=60, show_spinner=False)
def load_sensor_history():
    with st.spinner("📈 Loading Sensor History..."):
        return run_query("""
            SELECT * FROM GOLD.VW_SENSOR_HISTORY 
            WHERE READING_TIME >= DATEADD(day, -7, CURRENT_DATE())
            ORDER BY READING_TIME DESC LIMIT 5000
        """, "history")


@st.cache_data(ttl=30, show_spinner=False)
def load_aqi_status():
    with st.spinner("🚦 Loading AQI Status..."):
        return run_query("""
            SELECT 
                AQI_CATEGORY,
                COUNT(*) as SENSOR_COUNT,
                ROUND(AVG(AQI), 2) as AVG_AQI
            FROM GOLD.VW_AQI_STATUS
            GROUP BY AQI_CATEGORY
            ORDER BY AVG_AQI DESC
        """, "status")


@st.cache_data(ttl=30, show_spinner=False)
def load_pollutants():
    with st.spinner("🧪 Loading Pollutant Data..."):
        return run_query("""
            SELECT 
                ROUND(AVG(PM25), 2) as AVG_PM25,
                ROUND(AVG(PM10), 2) as AVG_PM10,
                ROUND(AVG(CO), 2) as AVG_CO,
                ROUND(AVG(NO2), 2) as AVG_NO2,
                ROUND(AVG(SO2), 2) as AVG_SO2,
                ROUND(AVG(O3), 2) as AVG_O3
            FROM GOLD.VW_POLLUTANT_SUMMARY
        """, "pollutants")


def error_banner(msg):
    st.markdown(
        f"""<div class="alert-banner" style="background: rgba(231,76,60,0.15);
        border: 1px solid rgba(231,76,60,0.4); color:#ff6b6b;">
        ⚠️ {msg}</div>""",
        unsafe_allow_html=True,
    )


# =====================================================================
# LOAD ALL DATA
# =====================================================================
st.info("⏳ Connecting to Snowflake and loading data... (may take 10-15 seconds on first load)")

try:
    summary_df, err_summary = load_summary()
    sensor_df_raw, err_sensor = load_latest_sensor()
    history_df, err_history = load_sensor_history()
    status_df, err_status = load_aqi_status()
    pollutant_df, err_pollutant = load_pollutants()
    
    # Display any connection errors
    if err_summary or err_sensor or err_history or err_status or err_pollutant:
        st.warning("""
        ⚠️ **Data Loading Issues Detected:**
        - Some views may not exist or credentials may be incorrect
        - Falling back to empty data display
        - **Solution:** Check if GOLD schema views are created in Snowflake
        """)
        print("🔍 Errors detected:")
        if err_summary:
            print(f"  • Summary: {err_summary}")
        if err_sensor:
            print(f"  • Sensor: {err_sensor}")
        if err_history:
            print(f"  • History: {err_history}")
        if err_status:
            print(f"  • Status: {err_status}")
        if err_pollutant:
            print(f"  • Pollutants: {err_pollutant}")
    else:
        st.success("✅ All data loaded successfully!")

except Exception as e:
    st.error(f"❌ Critical connection error: {str(e)}")
    print(f"Critical error: {str(e)}")
    summary_df, err_summary = pd.DataFrame(), str(e)
    sensor_df_raw, err_sensor = pd.DataFrame(), str(e)
    history_df, err_history = pd.DataFrame(), str(e)
    status_df, err_status = pd.DataFrame(), str(e)
    pollutant_df, err_pollutant = pd.DataFrame(), str(e)

sensor_df = sensor_df_raw.copy() if not sensor_df_raw.empty else pd.DataFrame()

# =====================================================================
# SIDEBAR — filters, refresh, download
# =====================================================================
st.sidebar.title("🎯 Dashboard Filters")
selected_sensor = st.sidebar.selectbox(
    "Select Sensor",
    ["All"] + list(sensor_df["SENSOR_ID"].unique()) if "SENSOR_ID" in sensor_df.columns else ["All"]
)
if selected_sensor != "All" and "SENSOR_ID" in sensor_df.columns:
    sensor_df = sensor_df[
        sensor_df["SENSOR_ID"] == selected_sensor
    ]

st.sidebar.markdown(
    """
    <div style="text-align:center; padding: 0.5rem 0 1.4rem 0;">
        <div style="font-size: 2.2rem;">🌍</div>
        <div style="color:#fff; font-weight:800; font-size:1.1rem;">AQI Control Panel</div>
        <div style="color:#93a3b8; font-size:0.8rem;">Real-time filters</div>
    </div>
    """,
    unsafe_allow_html=True,
)

city_col = find_col(sensor_df, ["CITY"])
sensor_col = find_col(sensor_df, ["SENSOR_ID"])
category_col = find_col(sensor_df, ["AQI_CATEGORY", "CATEGORY"])

city_options = ["All"] + sorted(sensor_df[city_col].dropna().unique().tolist()) if city_col and not sensor_df.empty else ["All"]
selected_city = st.sidebar.selectbox("🏙 City", city_options)

category_options = ["All"] + sorted(sensor_df[category_col].dropna().unique().tolist()) if category_col and not sensor_df.empty else ["All"]
selected_category = st.sidebar.selectbox("🎯 AQI Category", category_options)

if selected_city != "All" and city_col:
    sensor_df = sensor_df[sensor_df[city_col] == selected_city]
if selected_category != "All" and category_col:
    sensor_df = sensor_df[sensor_df[category_col] == selected_category]

st.sidebar.divider()

if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

if not sensor_df.empty:
    st.sidebar.download_button(
        "⬇️ Download Filtered CSV",
        data=sensor_df.to_csv(index=False).encode("utf-8"),
        file_name="aqi_filtered_data.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.sidebar.divider()
st.sidebar.caption("🔄 Auto-refreshing every 10 seconds")
st.sidebar.caption("Built with Streamlit + Snowflake + Plotly")

# =====================================================================
# HERO HEADER
# =====================================================================
st.markdown(
    """
    <div class="hero-banner">
        <div class="hero-title">🌍 Smart City AQI Dashboard</div>
        <div class="hero-subtitle">Karachi Smart Air Quality Monitoring System — Real-time insights from IoT sensors & OpenAQ</div>
        <div class="live-pill"><span class="live-dot"></span> LIVE DATA</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if err_summary:
    error_banner(f"Could not load GOLD.VW_CITY_AQI_SUMMARY — {err_summary}")
if err_sensor:
    error_banner(f"Could not load GOLD.VW_LATEST_SENSOR — {err_sensor}")

# =====================================================================
# KPI CARDS
# =====================================================================
st.markdown('<div class="section-header">📊 Key Performance Indicators</div>', unsafe_allow_html=True)

total_sensors = sensor_df[sensor_col].nunique() if sensor_col and not sensor_df.empty else 0
aqi_col = find_col(sensor_df, ["AQI"])
pm25_col = find_col(sensor_df, ["PM25", "PM2_5"])
pm10_col = find_col(sensor_df, ["PM10"])

avg_aqi = round(sensor_df[aqi_col].mean(), 1) if aqi_col and not sensor_df.empty else None
avg_pm25 = round(sensor_df[pm25_col].mean(), 1) if pm25_col and not sensor_df.empty else None
avg_pm10 = round(sensor_df[pm10_col].mean(), 1) if pm10_col and not sensor_df.empty else None
total_readings = int(summary_df.iloc[0].get("TOTAL_READINGS", 0)) if not summary_df.empty and "TOTAL_READINGS" in summary_df.columns else len(sensor_df)
highest_aqi = round(sensor_df[aqi_col].max(), 1) if aqi_col and not sensor_df.empty else None
lowest_aqi = round(sensor_df[aqi_col].min(), 1) if aqi_col and not sensor_df.empty else None

c1, c2, c3, c4 = st.columns(4)
kpi_card("📡", "Total Sensors", total_sensors if total_sensors else "N/A", c1)
kpi_card("🌫", "Average AQI", avg_aqi if avg_aqi is not None else "N/A", c2)
kpi_card("💨", "Average PM2.5", f"{avg_pm25} µg/m³" if avg_pm25 is not None else "N/A", c3)
kpi_card("🌪", "Average PM10", f"{avg_pm10} µg/m³" if avg_pm10 is not None else "N/A", c4)

c5, c6, c7 = st.columns(3)
kpi_card("🧾", "Total Readings", f"{total_readings:,}" if total_readings else "N/A", c5)
kpi_card("🔺", "Highest AQI", highest_aqi if highest_aqi is not None else "N/A", c6)
kpi_card("🔻", "Lowest AQI", lowest_aqi if lowest_aqi is not None else "N/A", c7)

st.write("")

# =====================================================================
# AQI GAUGE METER
# =====================================================================
st.markdown('<div class="section-header">🌡 AQI Gauge Meter</div>', unsafe_allow_html=True)

if avg_aqi is not None:
    gauge_color, gauge_label = aqi_zone_4(avg_aqi)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_aqi,
        number={"suffix": " AQI", "font": {"size": 40, "color": "#fff"}},
        title={"text": f"Current Status: {gauge_label}", "font": {"size": 18, "color": "#e5e9f0"}},
        gauge={
            "axis": {"range": [0, 500], "tickcolor": "#93a3b8", "tickfont": {"color": "#93a3b8"}},
            "bar": {"color": gauge_color, "thickness": 0.3},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 50], "color": "rgba(46,204,113,0.35)"},
                {"range": [51, 100], "color": "rgba(241,196,15,0.35)"},
                {"range": [101, 200], "color": "rgba(230,126,34,0.35)"},
                {"range": [201, 500], "color": "rgba(231,76,60,0.35)"},
            ],
            "threshold": {"line": {"color": "#fff", "width": 3}, "thickness": 0.85, "value": avg_aqi},
        },
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font_color="#e5e9f0",
        margin=dict(t=50, b=10, l=30, r=30), height=320,
    )
    st.plotly_chart(fig_gauge, use_container_width=True)
else:
    st.info("Gauge unavailable — no AQI data for current filters.")

st.write("")

# =====================================================================
# AQI SUMMARY TABLE & LIVE ALERTS
# =====================================================================
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown('<div class="section-header">📋 AQI Summary Table</div>', unsafe_allow_html=True)
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True, height=220)
    else:
        st.info("Summary table will appear once data is available.")

with col_right:
    st.markdown('<div class="section-header">🚨 Live AQI Alerts</div>', unsafe_allow_html=True)
    if avg_aqi is not None:
        color, label = aqi_color_fine(avg_aqi)
        st.markdown(
            f"""<div class="alert-banner" style="background:{color}22; border:1px solid {color}66; color:{color};">
            {label} — AQI {avg_aqi:.1f}</div>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("No alert data available yet.")

st.write("")

# =====================================================================
# AQI STATUS CARDS
# =====================================================================
st.markdown('<div class="section-header">🚦 AQI Status Overview</div>', unsafe_allow_html=True)

if not status_df.empty:
    st.dataframe(status_df, use_container_width=True, height=180)
else:
    zones = [("🟢 Good", "#2ecc71"), ("🟡 Moderate", "#f1c40f"), ("🟠 Unhealthy", "#e67e22"), ("🔴 Hazardous", "#e74c3c")]
    chips_html = "".join(
        f'<span class="status-chip" style="background:{c}22; color:{c};">{l}</span>' for l, c in zones
    )
    st.markdown(chips_html, unsafe_allow_html=True)
    st.caption("Status breakdown table unavailable — showing legend only.")

st.write("")

# =====================================================================
# CHARTS — Bar (avg AQI by city), PM2.5 vs PM10, Pollutant breakdown
# =====================================================================
city_col_summary = find_col(summary_df, ["CITY"]) if not summary_df.empty else None
if not summary_df.empty and city_col_summary:
    st.markdown('<div class="section-header">📊 Average AQI by City</div>', unsafe_allow_html=True)
    aqi_summary_col = find_col(summary_df, ["AVG_AQI"])
    if aqi_summary_col:
        fig = px.bar(
            summary_df, x=city_col_summary, y=aqi_summary_col, color=aqi_summary_col, text=aqi_summary_col,
            color_continuous_scale=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#9b59b6"],
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(
            xaxis_title="City", yaxis_title="Average AQI",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e5e9f0", margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.write("")
    st.markdown('<div class="section-header">🌫 PM2.5 vs PM10 Comparison</div>', unsafe_allow_html=True)
    pm25_s = find_col(summary_df, ["AVG_PM25", "AVG_PM2_5"])
    pm10_s = find_col(summary_df, ["AVG_PM10"])
    if pm25_s and pm10_s:
        fig2 = px.bar(
            summary_df, x=city_col_summary, y=[pm25_s, pm10_s], barmode="group",
            color_discrete_sequence=["#3498db", "#e67e22"],
        )
        fig2.update_layout(
            xaxis_title="City", yaxis_title="Pollution Level (µg/m³)",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e5e9f0", margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("PM2.5 / PM10 columns not available in summary view.")
else:
    st.info("City-level summary charts unavailable — GOLD.VW_CITY_AQI_SUMMARY returned no data.")

st.write("")

# =====================================================================
# POLLUTANT DASHBOARD (PM2.5, PM10, CO, NO2, SO2, O3)
# =====================================================================
st.markdown('<div class="section-header">🧪 Pollutant Dashboard</div>', unsafe_allow_html=True)

if err_pollutant:
    error_banner(f"Could not load GOLD.VW_POLLUTANT_SUMMARY — {err_pollutant}")
elif not pollutant_df.empty:
    pollutant_targets = {
        "PM2.5": ["PM25", "AVG_PM25", "PM2_5"],
        "PM10": ["PM10", "AVG_PM10"],
        "CO": ["CO", "AVG_CO"],
        "NO2": ["NO2", "AVG_NO2"],
        "SO2": ["SO2", "AVG_SO2"],
        "O3": ["O3", "AVG_O3"],
    }
    rows = []
    for label, candidates in pollutant_targets.items():
        col = find_col(pollutant_df, candidates)
        if col:
            val = pollutant_df[col].mean()
            rows.append({"Pollutant": label, "Value": val})

    if rows:
        pollutant_chart_df = pd.DataFrame(rows)
        fig3 = px.bar(
            pollutant_chart_df, x="Pollutant", y="Value", color="Value", text="Value",
            color_continuous_scale=["#2ecc71", "#e74c3c"],
        )
        fig3.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig3.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e5e9f0", margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No recognizable pollutant columns found in GOLD.VW_POLLUTANT_SUMMARY.")
else:
    st.info("No pollutant data available yet.")

st.write("")

# =====================================================================
# MAPS — Interactive Scatter Map & Heatmap
# =====================================================================
st.markdown('<div class="section-header">🗺 Karachi AQI Sensor Geo-Analytics</div>', unsafe_allow_html=True)

lat_col = find_col(sensor_df, ["LATITUDE", "LAT"])
lon_col = find_col(sensor_df, ["LONGITUDE", "LON", "LNG"])

if not sensor_df.empty and lat_col and lon_col and aqi_col:
    tab1, tab2 = st.tabs(["📍 Interactive Scatter Map", "🔥 AQI Heatmap"])

    with tab1:
        fig6 = px.scatter_mapbox(
            sensor_df,
            lat=lat_col,
            lon=lon_col,
            color=aqi_col,
            hover_name=sensor_col if sensor_col else None,
            hover_data=[category_col] if category_col in sensor_df.columns else None,
            zoom=9,
            size=aqi_col,
            mapbox_style="open-street-map",
            color_continuous_scale=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#9b59b6"],
        )
        fig6.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=10, b=10), font_color="#e5e9f0")
        st.plotly_chart(fig6, use_container_width=True)

    with tab2:
        fig5 = px.density_mapbox(
            sensor_df,
            lat=lat_col,
            lon=lon_col,
            z=aqi_col,
            radius=25,
            zoom=9,
            mapbox_style="open-street-map"
        )
        fig5.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=10, b=10), font_color="#e5e9f0")
        st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No sensor location data available for the selected filters.")

st.write("")

# =====================================================================
# HISTORICAL AQI TREND
# =====================================================================
st.markdown('<div class="section-header">📈 Historical AQI Trend</div>', unsafe_allow_html=True)

if err_history:
    error_banner(f"Could not load GOLD.VW_SENSOR_HISTORY — {err_history}")
elif not history_df.empty:
    hist_sensor_col = find_col(history_df, ["SENSOR_ID"])
    hist_time_col = find_col(history_df, ["READING_TIME", "RECORDED_AT", "TIMESTAMP", "READING_TIMESTAMP"])
    hist_aqi_col = find_col(history_df, ["AQI"])

    hist_filtered = history_df.copy()
    if selected_sensor != "All" and hist_sensor_col:
        hist_filtered = hist_filtered[hist_filtered[hist_sensor_col] == selected_sensor]

    if hist_time_col and hist_aqi_col and hist_sensor_col:
        fig_trend = px.line(
            hist_filtered.sort_values(hist_time_col), x=hist_time_col, y=hist_aqi_col,
            color=hist_sensor_col, markers=True,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_trend.update_layout(
            xaxis_title="Reading Time", yaxis_title="AQI",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e5e9f0", margin=dict(t=20, b=20),
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Expected columns (sensor, time, AQI) not found in GOLD.VW_SENSOR_HISTORY.")
else:
    st.info("No historical data available yet.")

st.write("")

# =====================================================================
# AQI RANKING TABLE — Top 10 / Bottom 10
# =====================================================================
st.markdown('<div class="section-header">🏆 AQI Ranking — Top & Bottom Sensors</div>', unsafe_allow_html=True)

if not sensor_df.empty and aqi_col and sensor_col:
    rank_cols = [c for c in [sensor_col, city_col, aqi_col, category_col] if c]
    ranked = sensor_df[rank_cols].dropna(subset=[aqi_col]).sort_values(aqi_col, ascending=False)

    rc1, rc2 = st.columns(2)
    with rc1:
        st.caption("🔺 Top 10 — Highest AQI")
        st.dataframe(ranked.head(10).reset_index(drop=True), use_container_width=True, height=280)
    with rc2:
        st.caption("🔻 Bottom 10 — Lowest AQI")
        st.dataframe(ranked.tail(10).sort_values(aqi_col).reset_index(drop=True), use_container_width=True, height=280)
else:
    st.info("Ranking table unavailable — no sensor AQI data for current filters.")

st.write("")

# =====================================================================
# DOWNLOADS — CSV & PDF REPORT
# =====================================================================
st.markdown('<div class="section-header">⬇️ Reports & Downloads</div>', unsafe_allow_html=True)

col_dl1, col_dl2 = st.columns(2)

with col_dl1:
    if not sensor_df.empty:
        st.download_button(
            "⬇️ Download CSV Data",
            data=sensor_df.to_csv(index=False).encode("utf-8"),
            file_name="karachi_aqi.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.button("⬇️ Download CSV Data", disabled=True, use_container_width=True)

with col_dl2:
    def build_pdf_report():
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            )

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("TitleX", parent=styles["Title"], textColor=colors.HexColor("#1e3a5f"))
            elements = []

            elements.append(Paragraph("Smart City AQI Dashboard — Report", title_style))
            elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
            elements.append(Spacer(1, 14))

            elements.append(Paragraph("Key Statistics", styles["Heading2"]))
            stats_data = [
                ["Metric", "Value"],
                ["Total Sensors", str(total_sensors)],
                ["Average AQI", str(avg_aqi) if avg_aqi is not None else "N/A"],
                ["Average PM2.5", str(avg_pm25) if avg_pm25 is not None else "N/A"],
                ["Average PM10", str(avg_pm10) if avg_pm10 is not None else "N/A"],
                ["Total Readings", str(total_readings)],
                ["Highest AQI", str(highest_aqi) if highest_aqi is not None else "N/A"],
                ["Lowest AQI", str(lowest_aqi) if lowest_aqi is not None else "N/A"],
            ]
            stats_table = Table(stats_data, colWidths=[8 * cm, 6 * cm])
            stats_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]))
            elements.append(stats_table)
            elements.append(Spacer(1, 16))

            if not summary_df.empty:
                elements.append(Paragraph("City AQI Summary", styles["Heading2"]))
                summary_preview = summary_df.head(10)
                table_data = [list(summary_preview.columns)] + summary_preview.astype(str).values.tolist()
                sum_table = Table(table_data, repeatRows=1)
                sum_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d5f8a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ]))
                elements.append(sum_table)
                elements.append(Spacer(1, 16))

            if not sensor_df.empty and aqi_col:
                elements.append(Paragraph("Top 10 Highest AQI Sensors", styles["Heading2"]))
                rank_cols_pdf = [c for c in [sensor_col, city_col, aqi_col, category_col] if c]
                top10 = sensor_df[rank_cols_pdf].dropna(subset=[aqi_col]).sort_values(aqi_col, ascending=False).head(10)
                top_data = [rank_cols_pdf] + top10.astype(str).values.tolist()
                top_table = Table(top_data, repeatRows=1)
                top_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e67e22")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ]))
                elements.append(top_table)

            doc.build(elements)
            buffer.seek(0)
            return buffer, None
        except Exception as e:
            return None, str(e)

    pdf_buffer, pdf_err = build_pdf_report()
    if pdf_buffer:
        st.download_button(
            "📄 Download PDF Report",
            data=pdf_buffer,
            file_name=f"aqi_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.button("📄 Download PDF Report", disabled=True, use_container_width=True)
        if pdf_err:
            st.caption(f"PDF generation unavailable: {pdf_err}")

st.write("")

# =====================================================================
# STATUS FOOTER
# =====================================================================
any_data = not (sensor_df.empty and summary_df.empty and history_df.empty)
if any_data:
    st.success("✅ Data loaded successfully from Snowflake — auto-refreshing every 10 seconds.")
else:
    st.error("❌ No data loaded. Check Snowflake connection, credentials, and view names.")

st.markdown(
    """
    <div class="footer-box">
        <b>Smart City AQI Dashboard</b><br>
        Powered by Python · Streamlit · Snowflake · Plotly
    </div>
    """,
    unsafe_allow_html=True,
)