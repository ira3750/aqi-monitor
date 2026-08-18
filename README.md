# AQI Monitor

Real-time air quality monitoring system built on an ESP32 with PMS5003 and DHT22 sensors. Reads PM2.5, PM10, temperature, and humidity every 30 seconds, computes AQI using the CPCB standard, and displays live and historical data on a web dashboard.

**Live dashboard:** https://your-streamlit-url.streamlit.app

---

## Architecture

```
[ESP32 + PMS5003 + DHT22]
        │  HTTPS POST every 30s
        ▼
[FastAPI backend] — validates data, computes AQI
        │  writes to
        ▼
[PostgreSQL] — time-series readings
        │  reads from
        ▼
[Streamlit dashboard] — live charts, auto-refresh
```

---

## Dashboard

![Current AQI](screenshots/current.png)
![Historical charts](screenshots/history.png)

---

## Features

- Live AQI display with category and colour coding
- Historical charts for AQI, PM 2.5, humidity
- Fault-tolerant firmware: buffers up to 20 readings in memory during WiFi outages and flushes on reconnect
- Idempotent ingestion: `ON CONFLICT DO UPDATE` prevents duplicate rows when the device retries a POST
- Input validation at the API boundary rejects physically implausible sensor values before they reach the database
- Dashboard auto-refreshes every 30 seconds

---

## Tech stack

| Layer | Technology |
|---|---|
| Firmware | MicroPython on ESP32 |
| Backend | FastAPI, psycopg2 |
| Database | PostgreSQL |
| Dashboard | Streamlit, Plotly |
| Hosting | Render (backend + DB), Streamlit Community Cloud |

---

## Hardware

| Component | Role |
|---|---|
| ESP32 DevKit | Microcontroller, WiFi |
| Plantower PMS5003 | PM2.5 and PM10 (UART) |
| DHT22 | Temperature and humidity (GPIO) |

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/readings` | Ingest a sensor reading from the device |
| `GET` | `/readings/latest` | Most recent reading for a device |
| `GET` | `/readings/history?hours=24` | Readings over the last N hours (max 168) |

Interactive docs available at `/docs` on the live backend.

---

## Running locally

**Prerequisites:** Python 3.11+, PostgreSQL running locally.

```bash
# clone
git clone https://github.com/your-username/aqi-monitor.git
cd aqi-monitor
```

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/aqi_monitor
```

Run the schema migration:
```bash
psql -U postgres -d aqi_monitor -f schema.sql
```

Start the server:
```bash
uvicorn main:app --reload --host 0.0.0.0
```

**Dashboard:**
```bash
cd dashboard
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Create `dashboard/.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/aqi_monitor
```

```bash
streamlit run app.py
```

**Firmware:** flash MicroPython onto the ESP32, update `firmware/config.py` with your WiFi credentials and backend URL, then upload `firmware/main.py` via Thonny.

---

## Future improvements

- Persistent flash-based buffer on the ESP32 to survive device reboots without losing queued readings
- MQTT transport for multi-device ingestion without polling
- TimescaleDB migration when scaling beyond a single sensor
- Telegram or email alerts when AQI crosses a threshold
- Hourly AQI averages using a scheduled job

