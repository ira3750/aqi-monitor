import streamlit as st
from streamlit_autorefresh import st_autorefresh
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv

load_dotenv()

# Use Streamlit secrets in production, .env locally
DATABASE_URL = st.secrets.get("DATABASE_URL") or os.getenv("DATABASE_URL")


# ── auto-refresh ───────────────────────────────────────────────────────────────
st_autorefresh(interval=30 * 1000, key="aqi_refresh")

# ── AQI categories ─────────────────────────────────────────────────────────────
AQI_CATEGORIES = [
    (0, 50, "Good", "#00e400"),
    (51, 100, "Satisfactory", "#ffff00"),
    (101, 200, "Moderate", "#ff7e00"),
    (201, 300, "Poor", "#ff0000"),
    (301, 400, "Very Poor", "#8f3f97"),
    (401, 500, "Severe", "#7e0023"),
]


def get_category(aqi):
    for low, high, label, color in AQI_CATEGORIES:
        if low <= aqi <= high:
            return label, color
    return "Unknown", "#999999"


# ── database ───────────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(DATABASE_URL)


@st.cache_data(ttl=30)
def fetch_latest():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM readings
        ORDER BY recorded_at DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    cur.close()
    conn.close()

    return dict(row) if row else None


@st.cache_data(ttl=30)
def fetch_history(hours: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT *
        FROM readings
        WHERE recorded_at >= now() - interval '%s hours'
        ORDER BY recorded_at ASC
        """,
        (hours,),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return pd.DataFrame([dict(r) for r in rows])


# ── page ───────────────────────────────────────────────────────────────────────
st.title("AQI Monitor")
st.caption("Updates every 30 seconds")

latest = fetch_latest()

if latest is None:
    st.warning("No readings yet. Is the ESP32 running?")
    st.stop()

# current AQI block
aqi = latest.get("aqi")

if aqi is not None:
    label, color = get_category(aqi)

    st.markdown(
        f"""
        <div style="
            background-color: {color};
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        ">
            <h1 style="color: white; margin: 0;">{aqi}</h1>
            <p style="color: white; font-size: 1.2em; margin: 0;">{label}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# raw values
col1, col2, col3, col4 = st.columns(4)

col1.metric("PM2.5", f"{latest.get('pm25', 'N/A')} μg/m³")
col2.metric("PM10", f"{latest.get('pm10', 'N/A')} μg/m³")
col3.metric("Temp", f"{latest.get('temperature', 'N/A')} °C")
col4.metric("Humidity", f"{latest.get('humidity', 'N/A')} %")

st.divider()

# history
st.subheader("History")

hours = st.slider("Hours to display", min_value=1, max_value=168, value=24)

df = fetch_history(hours)

if df.empty:
    st.info("No data for this time range.")
    st.stop()


def line_chart(df, column, title, unit):
    fig = px.line(
        df,
        x="recorded_at",
        y=column,
        title=title,
        labels={"recorded_at": "Time", column: unit},
    )
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)


line_chart(df, "pm25", "PM2.5", "μg/m³")
line_chart(df, "pm10", "PM10", "μg/m³")
line_chart(df, "temperature", "Temperature", "°C")
line_chart(df, "humidity", "Humidity", "%")
