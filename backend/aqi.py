# CPCB (India) AQI breakpoints for PM2.5 (μg/m³ over 24hr average)
# Format: (C_low, C_high, I_low, I_high)


PM25_BREAKPOINTS = [ 
    (0, 30, 0, 50), 
    (30, 60, 51, 100), 
    (60, 90, 101, 200), 
    (90, 120, 201, 300), 
    (120, 250, 301, 400), 
    (250, 500, 401, 500),]
# AQI categories for display on the dashboard
AQI_CATEGORIES = [ 
    (0, 50, "Good", "#00e400"), 
    (51, 100, "Satisfactory", "#ffff00"), 
    (101, 200, "Moderate", "#ff7e00"), 
    (201, 300, "Poor", "#ff0000"), 
    (301, 400, "Very Poor", "#8f3f97"), 
    (401, 500, "Severe", "#7e0023"),]

def compute_aqi(pm25: float) -> int | None: 
    for (c_low, c_high, i_low, i_high) in PM25_BREAKPOINTS: 
        if c_low <= pm25 <= c_high: 
            aqi = ((i_high - i_low) / (c_high - c_low)) * (pm25 - c_low) + i_low 
            return round(aqi) 
    return None # out of range — store as null rather than a wrong number

def get_category(aqi: int) -> dict: 
    for (low, high, label, color) in AQI_CATEGORIES: 
        if low <= aqi <= high: 
            return {"label": label, "color": color} 
    return {"label": "Unknown", "color": "#999999"}