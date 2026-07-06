from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from models import SensorReading
from database import get_connection, RealDictCursor
from aqi import compute_aqi

app = FastAPI()


@app.get("/")
def root():
    return {"status": "AQI monitor backend running"}


@app.post("/readings", status_code=200)
def create_reading(reading: SensorReading):
    # Convert Unix timestamp from device to a proper datetime
    recorded_at = datetime.fromtimestamp(
        reading.recorded_at,
        tz=timezone.utc
    )

    aqi = compute_aqi(reading.pm25) if reading.pm25 is not None else None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO readings (
                device_id,
                recorded_at,
                pm25,
                pm10,
                temperature,
                humidity,
                aqi
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (device_id, recorded_at)
            DO UPDATE SET
                pm25 = EXCLUDED.pm25,
                pm10 = EXCLUDED.pm10,
                temperature = EXCLUDED.temperature,
                humidity = EXCLUDED.humidity,
                aqi = EXCLUDED.aqi
            """,
            (
                reading.device_id,
                recorded_at,
                reading.pm25,
                reading.pm10,
                reading.temperature,
                reading.humidity,
                aqi,
            ),
        )

        conn.commit()
        cur.close()
        conn.close()

        return {"status": "ok"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/readings/latest")
def get_latest(device_id: str = "esp32-01"):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT *
            FROM readings
            WHERE device_id = %s
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (device_id,),
        )

        row = cur.fetchone()

        cur.close()
        conn.close()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="No readings found"
            )

        return dict(row)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/readings/history")
def get_history(device_id: str = "esp32-01", hours: int = 24):
    # Cap at one week—don't let the dashboard query everything
    if hours > 168:
        hours = 168

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT *
            FROM readings
            WHERE device_id = %s
              AND recorded_at >= now() - interval '%s hours'
            ORDER BY recorded_at ASC
            """,
            (device_id, hours),
        )

        rows = cur.fetchall()

        cur.close()
        conn.close()

        return [dict(r) for r in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  