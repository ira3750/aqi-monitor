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

# ── page config ──
st.set_page_config(
    page_title="AQI Monitor",
    page_icon="🌬️",
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

# ── data ─
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

# ── css ───────────────
st.markdown("""
<style>
    /* tighten default Streamlit padding */
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    /* header row */
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
    .dash-location {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.6);
    }
    .dash-updated {
        font-size: 0.8rem;
        color: rgba(255,255,255,0.5);
    }

    /* AQI hero block */
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
    }
    .aqi-label {
        font-size: 1rem;
        color: rgba(255,255,255,0.9);
        font-weight: 500;
        margin-top: 0.25rem;
    }
    .aqi-description {
        font-size: 0.8rem;
        color: rgba(255,255,255,0.75);
        margin-top: 0.2rem;
    }

    /* metric cards */
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
        border: 1px solid #ececec;
    }
    .metric-label {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #888;
        margin-bottom: 0.3rem;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 600;
        color: #1a1a1a;
        line-height: 1;
    }
    .metric-unit {
        font-size: 0.78rem;
        color: #999;
        margin-top: 0.2rem;
    }

    /* section labels */
    .section-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #999;
        margin-bottom: 0.75rem;
        margin-top: 0.25rem;
    }

    /* time range buttons */
    div[data-testid="column"] button {
        width: 100%;
        border-radius: 6px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ── fetch data ──
latest = fetch_latest()

# ── header ─────
IST = timezone(timedelta(hours=5, minutes=30))
now_str = datetime.now(IST).strftime("%H:%M IST")
location = "PG Girls Hostel, MNNIT Campus"   

if latest and latest.get("recorded_at"):
    recorded_at = latest["recorded_at"]
    if hasattr(recorded_at, "timestamp"):
        age_seconds = int((datetime.now(timezone.utc) - recorded_at.replace(tzinfo=timezone.utc) if recorded_at.tzinfo is None else datetime.now(timezone.utc) - recorded_at).total_seconds())
    else:
        age_seconds = 0
    if age_seconds < 60:
        updated_str = f"Updated {age_seconds}s ago"
    elif age_seconds < 3600:
        updated_str = f"Updated {age_seconds // 60}m ago"
    else:
        updated_str = f"Updated {age_seconds // 3600}h ago"
else:
    updated_str = "No data yet"

st.markdown(f"""
<div class="dash-header">
    <div>
        <span class="dash-title">Air Quality Monitor</span>
        <span class="dash-location" style="margin-left:0.75rem;">📍 {location}</span>
    </div>
    <span class="dash-updated">{updated_str} &nbsp;·&nbsp; {now_str}</span>
</div>
""", unsafe_allow_html=True)

# ── no data state ──────────
if latest is None:
    st.markdown("""
    <div style="text-align:center; padding: 3rem; color: #999;">
        <div style="font-size:2.5rem; margin-bottom:0.75rem;">📡</div>
        <div style="font-size:1rem; font-weight:500; color:#555;">No readings yet</div>
        <div style="font-size:0.85rem; margin-top:0.4rem;">
            Power on the ESP32 and confirm it can reach the backend.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


#aqi comments
aqi = latest.get("aqi")

AQI_DESCRIPTIONS = {
    "Good":         "Air quality is satisfactory. Outdoor activity is safe.",
    "Satisfactory": "Acceptable air quality. Sensitive individuals may notice mild effects.",
    "Moderate":     "Sensitive groups should limit prolonged outdoor exertion.",
    "Poor":         "Everyone may begin to experience health effects outdoors.",
    "Very Poor":    "Health alert: everyone may experience serious effects.",
    "Severe":       "Health warnings of emergency conditions. Stay indoors.",
}

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

# ── metric cards ───────
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

# ── history section ───────
st.markdown('<div class="section-label">History</div>', unsafe_allow_html=True)

# time range selector as buttons
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

# ── charts ─────────────────────
chart_height = 260
col_left, col_right = st.columns(2)

# PM2.5 + PM10 
with col_left:
    fig_pm = go.Figure()
    if "pm25" in df.columns and not df["pm25"].isna().all():
        fig_pm.add_trace(go.Scatter(
            x=df["recorded_at"], y=df["pm25"],
            name="PM 2.5",
            line=dict(color="#e74c3c", width=1.5),
            hovertemplate="%{y:.0f} µg/m³<extra>PM 2.5</extra>"
        ))
    if "pm10" in df.columns and not df["pm10"].isna().all():
        fig_pm.add_trace(go.Scatter(
            x=df["recorded_at"], y=df["pm10"],
            name="PM 10",
            line=dict(color="#e67e22", width=1.5, dash="dot"),
            hovertemplate="%{y:.0f} µg/m³<extra>PM 10</extra>"
        ))
    fig_pm.update_layout(
        title=dict(text="Particulate Matter", font=dict(size=13)),
        height=chart_height,
        margin=dict(l=0, r=0, t=36, b=0),
        legend=dict(orientation="h", y=-0.2, x=0),
        yaxis=dict(title="µg/m³", title_font=dict(size=11)),
        xaxis=dict(title=""),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
    )
    fig_pm.update_xaxes(showgrid=False)
    fig_pm.update_yaxes(gridcolor="#f0f0f0")
    st.plotly_chart(fig_pm, use_container_width=True)

# Temperature + Humidity 
with col_right:
    fig_clim = go.Figure()
    if "temperature" in df.columns and not df["temperature"].isna().all():
        fig_clim.add_trace(go.Scatter(
            x=df["recorded_at"], y=df["temperature"],
            name="Temp",
            yaxis="y1",
            line=dict(color="#3498db", width=1.5),
            hovertemplate="%{y:.1f} °C<extra>Temp</extra>"
        ))
    if "humidity" in df.columns and not df["humidity"].isna().all():
        fig_clim.add_trace(go.Scatter(
            x=df["recorded_at"], y=df["humidity"],
            name="Humidity",
            yaxis="y2",
            line=dict(color="#2ecc71", width=1.5, dash="dot"),
            hovertemplate="%{y:.1f}%<extra>Humidity</extra>"
        ))
    fig_clim.update_layout(
        title=dict(text="Temperature & Humidity", font=dict(size=13)),
        height=chart_height,
        margin=dict(l=0, r=0, t=36, b=0),
        legend=dict(orientation="h", y=-0.2, x=0),
        yaxis=dict(title="°C", title_font=dict(size=11), gridcolor="#f0f0f0"),
        yaxis2=dict(title="% RH", title_font=dict(size=11), overlaying="y", side="right", showgrid=False),
        xaxis=dict(title=""),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
    )
    fig_clim.update_xaxes(showgrid=False)
    st.plotly_chart(fig_clim, use_container_width=True)
