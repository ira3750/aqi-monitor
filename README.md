# AQI Monitor

Real-time air quality monitoring system built on an ESP32 with PMS5003 and DHT22 sensors.

**Live dashboard:** https://aqi-monitor-m55prumndugr5sfaxaypbm.streamlit.app/

## Architecture

ESP32 (MicroPython firmware) -> FastAPI backend -> PostgreSQL -> Streamlit dashboard

The device reads PM2.5, PM10, temperature, and humidity every 30 seconds and POSTs readings over WiFi to a REST API. The backend validates incoming data, computes AQI using the CPCB standard breakpoint formula, and stores readings with idempotent writes to handle device retries safely. The dashboard reads directly from the database and auto-refreshes every 30 seconds.

## Design decisions

- **HTTP over MQTT:** Single device, no pub/sub fanout needed. HTTP is simpler to debug and reason about at this scale.
- **Plain PostgreSQL over TimescaleDB:** ~1,440 rows/day doesn't justify Timescale's complexity. 
- **Idempotent ingestion:** `ON CONFLICT DO UPDATE` prevents duplicate rows when the device retries a POST after not receiving an ACK.
- **Device-side buffering:** Up to 20 readings are buffered in memory and flushed when connectivity resumes, so a WiFi outage doesn't silently drop data.
- **AQI computed at write time:** Single source of truth — every consumer gets the same value without recomputing it.

## Stack

- **Firmware:** MicroPython on ESP32
- **Backend:** FastAPI, psycopg2
- **Database:** PostgreSQL
- **Dashboard:** Streamlit, Plotly
- **Hosting:** Render (backend + DB), Streamlit Community Cloud (dashboard)
