import streamlit as st
from streamlit_autorefresh import st_autorefresh
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = st.secrets.get("DATABASE_URL") if hasattr(st, "secrets") else None
if not DATABASE_URL:
    DATABASE_URL = os.getenv("DATABASE_URL")

#page config
st.set_page_config(
    page_title="AQI Monitor",
    layout="wide",
)

st_autorefresh(interval=30 * 1000, key="aqi_refresh")


AQI_CATEGORIES = [
    (0,   50,  "Good",         "#2ecc71"),
    (51,  100, "Satisfactory", "#f1c40f"),
    (101, 200, "Moderate",     "#e67e22"),
    (201, 300, "Poor",         "#e74c3c"),
    (301, 400, "Very Poor",    "#8e44ad"),
    (401, 500, "Severe",       "#7e0023"),
]

def get_category(aqi):
    for low, high, label, color in AQI_CATEGORIES:
        if low <= aqi <= high:
            return label, color
    return "Unknown", "#95a5a6"

def aqi_color(val):
    for low, high, _, color in AQI_CATEGORIES:
        if val is not None and low <= val <= high:
            return color
    return "#95a5a6"

# database
def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

@st.cache_data(ttl=30)
def fetch_latest():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM readings ORDER BY recorded_at DESC LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

@st.cache_data(ttl=30)
def fetch_history(hours: int):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM readings
            WHERE recorded_at >= now() - (%s * interval '1 hour')
            ORDER BY recorded_at ASC
        """, (hours,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return pd.DataFrame([dict(r) for r in rows])
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return pd.DataFrame()

# css
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    .dash-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.25rem;
        background: #1a1a2e;
        border-radius: 8px;
        padding: 0.85rem 1.25rem;
    }
    .dash-title {
        font-size: 1rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }
    .dash-meta {
        text-align: right;
        line-height: 1.6;
    }
    .dash-location {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.9);
        display: block;
    }
    .dash-time {
        font-size: 0.78rem;
        color: rgba(255,255,255,0.75);
        display: block;
    }
    .dash-updated {
        font-size: 0.75rem;
        color: rgba(255,255,255,0.55);
        display: block;
    }

    .aqi-block {
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 1.25rem;
        margin-bottom: 1.25rem;
    }
    .aqi-number {
        font-size: 3rem;
        font-weight: 700;
        color: white;
        line-height: 1;
        text-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .aqi-label {
        font-size: 1rem;
        color: rgba(255,255,255,0.95);
        font-weight: 600;
        margin-top: 0.25rem;
    }
    .aqi-description {
        font-size: 0.8rem;
        color: rgba(255,255,255,0.8);
        margin-top: 0.2rem;
    }

    .metric-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f8f8f8;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        border: 1px solid #e8e8e8;
    }
    .metric-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #777;
        margin-bottom: 0.3rem;
        font-weight: 500;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #111;
        line-height: 1;
    }
    .metric-unit {
        font-size: 0.78rem;
        color: #888;
        margin-top: 0.25rem;
        font-weight: 400;
    }

    .section-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #aaa;
        margin-bottom: 0.75rem;
        margin-top: 0.5rem;
        font-weight: 600;
    }

    /* humidity note */
    .humidity-note {
        font-size: 0.72rem;
        color: #aaa;
        margin-top: 0.25rem;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# fetch
latest = fetch_latest()

# header
IST = timezone(timedelta(hours=5, minutes=30))
now_str = datetime.now(IST).strftime("%H:%M IST")
location = "PG Girls Hostel, MNNIT Campus"

if latest and latest.get("recorded_at"):
    recorded_at = latest["recorded_at"]
    if hasattr(recorded_at, "tzinfo"):
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)
        age_seconds = int((datetime.now(timezone.utc) - recorded_at).total_seconds())
    else:
        age_seconds = 0
    if age_seconds < 60:
        updated_str = f"Updated {age_seconds}s ago"
    elif age_seconds < 3600:
        updated_str = f"Updated {age_seconds // 60}m ago"
    else:
        updated_str = f"Updated {age_seconds // 3600}h ago"
else:
    updated_str = "Awaiting first reading"

st.markdown(f"""
<div class="dash-header">
    <span class="dash-title">Air Quality Monitor</span>
    <div class="dash-meta">
        <span class="dash-location">📍 {location}</span>
        <span class="dash-time">Current time: {now_str}</span>
        <span class="dash-updated">{updated_str}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# no data
if latest is None:
    st.markdown("""
    <div style="text-align:center; padding:3rem; color:#999;">
        <div style="font-size:2.5rem; margin-bottom:0.75rem;">📡</div>
        <div style="font-size:1rem; font-weight:500; color:#555;">No readings yet</div>
        <div style="font-size:0.85rem; margin-top:0.4rem;">
            Power on the ESP32 and confirm it can reach the backend.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# AQI block
AQI_DESCRIPTIONS = {
    "Good":         "Air quality is satisfactory. Outdoor activity is safe.",
    "Satisfactory": "Acceptable air quality. Sensitive individuals may notice mild effects.",
    "Moderate":     "Sensitive groups should limit prolonged outdoor exertion.",
    "Poor":         "Everyone may begin to experience health effects outdoors.",
    "Very Poor":    "Health alert: everyone may experience serious effects.",
    "Severe":       "Health warnings of emergency conditions. Stay indoors.",
}

aqi = latest.get("aqi")
if aqi is not None:
    label, color = get_category(aqi)
    description = AQI_DESCRIPTIONS.get(label, "")
    st.markdown(f"""
    <div class="aqi-block" style="background:{color};">
        <div class="aqi-number">{aqi}</div>
        <div>
            <div class="aqi-label">{label}</div>
            <div class="aqi-description">{description}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning("AQI could not be computed for the latest reading.")

# metric cards
def fmt(val, decimals=1):
    return f"{val:.{decimals}f}" if val is not None else "—"

st.markdown(f"""
<div class="metric-row">
    <div class="metric-card">
        <div class="metric-label">PM 2.5</div>
        <div class="metric-value">{fmt(latest.get('pm25'), 0)}</div>
        <div class="metric-unit">µg/m³</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">PM 10</div>
        <div class="metric-value">{fmt(latest.get('pm10'), 0)}</div>
        <div class="metric-unit">µg/m³</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Temperature</div>
        <div class="metric-value">{fmt(latest.get('temperature'))}</div>
        <div class="metric-unit">°C</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Humidity</div>
        <div class="metric-value">{fmt(latest.get('humidity'))}</div>
        <div class="metric-unit">% RH</div>
    </div>
</div>
""", unsafe_allow_html=True)

# history
st.markdown('<div class="section-label">History</div>', unsafe_allow_html=True)

RANGES = {"1 hr": 1, "6 hrs": 6, "24 hrs": 24, "7 days": 168}
if "selected_range" not in st.session_state:
    st.session_state.selected_range = "24 hrs"

cols = st.columns(len(RANGES))
for col, (label, hours) in zip(cols, RANGES.items()):
    if col.button(label, use_container_width=True):
        st.session_state.selected_range = label

selected_hours = RANGES[st.session_state.selected_range]
df = fetch_history(selected_hours)

if df.empty:
    st.markdown("""
    <div style="text-align:center; padding:2rem; color:#bbb; font-size:0.9rem;">
        No readings in this time range.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# AQI bar chart
if "aqi" in df.columns and not df["aqi"].isna().all():
    aqi_df = df.dropna(subset=["aqi"])
    fig_aqi = go.Figure(go.Bar(
        x=aqi_df["recorded_at"],
        y=aqi_df["aqi"],
        marker_color=[aqi_color(v) for v in aqi_df["aqi"]],
        hovertemplate="%{y:.0f}<extra>AQI</extra>",
        showlegend=False,
    ))
    fig_aqi.update_layout(
        title=dict(text="AQI", font=dict(size=13, color="#333")),
        height=220,
        margin=dict(l=0, r=0, t=36, b=0),
        yaxis=dict(
            title="AQI",
            title_font=dict(size=11, color="#555"),
            tickfont=dict(size=10, color="#555"),
            range=[0, 500],
            gridcolor="#f0f0f0",
        ),
        xaxis=dict(tickfont=dict(size=10, color="#555")),
        plot_bgcolor="white",
        paper_bgcolor="white",
        bargap=0.15,
    )
    fig_aqi.update_xaxes(showgrid=False)
    st.plotly_chart(fig_aqi, use_container_width=True)

# PM2.5 and Humidity side by side 
col_left, col_right = st.columns(2)

with col_left:
    fig_pm = go.Figure()
    if "pm25" in df.columns and not df["pm25"].isna().all():
        fig_pm.add_trace(go.Scatter(
            x=df["recorded_at"],
            y=df["pm25"],
            name="PM 2.5",
            line=dict(color="#e74c3c", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(231,76,60,0.08)",
            hovertemplate="%{y:.0f} µg/m³<extra>PM 2.5</extra>",
        ))
    fig_pm.update_layout(
        title=dict(text="PM 2.5", font=dict(size=13, color="#333")),
        height=240,
        margin=dict(l=0, r=0, t=36, b=0),
        yaxis=dict(
            title="µg/m³",
            title_font=dict(size=11, color="#555"),
            tickfont=dict(size=10, color="#555"),
            gridcolor="#f0f0f0",
        ),
        xaxis=dict(tickfont=dict(size=10, color="#555")),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        showlegend=False,
    )
    fig_pm.update_xaxes(showgrid=False)
    st.plotly_chart(fig_pm, use_container_width=True)

with col_right:
    fig_hum = go.Figure()
    if "humidity" in df.columns and not df["humidity"].isna().all():
        fig_hum.add_trace(go.Scatter(
            x=df["recorded_at"],
            y=df["humidity"],
            name="Humidity",
            line=dict(color="#3498db", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(52,152,219,0.08)",
            hovertemplate="%{y:.1f}%<extra>Humidity</extra>",
        ))
    fig_hum.update_layout(
        title=dict(text="Humidity", font=dict(size=13, color="#333")),
        height=240,
        margin=dict(l=0, r=0, t=36, b=0),
        yaxis=dict(
            title="% RH",
            title_font=dict(size=11, color="#555"),
            tickfont=dict(size=10, color="#555"),
            range=[0, 100],
            gridcolor="#f0f0f0",
        ),
        xaxis=dict(tickfont=dict(size=10, color="#555")),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        showlegend=False,
    )
    fig_hum.update_xaxes(showgrid=False)
    st.plotly_chart(fig_hum, use_container_width=True)

st.markdown("""
<div class="humidity-note">
    ⚠️ PM readings may be elevated when humidity exceeds 80% RH — 
    water droplets scatter the sensor laser similarly to particulate matter.
</div>
""", unsafe_allow_html=True)
