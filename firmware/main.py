import time
import network
import ntptime
import urequests
import ujson
import dht
from machine import UART, Pin
from config import WIFI_SSID, WIFI_PASSWORD, BACKEND_URL, DEVICE_ID


# ─── constants ───────────────────────────

READ_INTERVAL   = 30        #seconds between readings
MAX_BUFFER      = 20        #max readings to hold if WiFi is down
WIFI_TIMEOUT    = 15        #seconds to wait for WiFi before giving up
POST_TIMEOUT    = 5         #seconds before an HTTP POST gives up
UNIX_OFFSET     = 946684800 #different UNIX epoch

#PMS5003 warm-up period:
WARMUP_SECONDS  = 30


# ─── PMS5003 ─────────────────────────────

class PMS5003:
    def __init__(self, uart_id=2, tx=17, rx=16):
        self.uart = UART(
            uart_id,
            baudrate=9600,
            tx=Pin(tx),
            rx=Pin(rx)
        )

    def read(self):
        #Scan for frame header. Helps keep in sync even if buffer has multiple frames/we are mid frame
        while self.uart.any() >= 32:
            b = self.uart.read(1)
            if b[0] != 0x42:
                continue                     

            if self.uart.any() < 31:
                return None                  #not enough data left for a full frame

            rest = self.uart.read(31)
            if rest[0] != 0x4D:
                continue                     #second header byte wrong

            data = b + rest

            checksum = (data[30] << 8) | data[31]
            if sum(data[0:30]) != checksum:
                continue                     #corrupted frame, discard

            #bytes 12-13: PM2.5, bytes 14-15: PM10
            pm25 = (data[12] << 8) | data[13]
            pm10 = (data[14] << 8) | data[15]
            return pm25, pm10

        return None                     


# ─── DHT22 ─────────────────────────────

dht_sensor = dht.DHT22(Pin(4))

def read_dht22():
    try:
        dht_sensor.measure()
        return dht_sensor.temperature(), dht_sensor.humidity()
    except Exception as e:
        print("DHT22 read failed:", e)
        return None, None


# ─── WiFi ───────────────────────
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)   # reset the interface first
    time.sleep(0.5)
    wlan.active(True)
    if wlan.isconnected():
        return True
    print("Connecting to WiFi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > WIFI_TIMEOUT:
            print("WiFi connection timed out.")
            return False
        time.sleep(0.5)
    print("WiFi connected:", wlan.ifconfig()[0])
    return True


# ─── time ────────────────────────────────────────────

def sync_time():
    try:
        ntptime.settime()
        print("Time synced.")
    except Exception as e:
        print("NTP sync failed:", e)

def unix_timestamp():
    return time.time() + UNIX_OFFSET


# ─── HTTP ───────────────────────────────

def send_reading(payload):
    try:
        resp = urequests.post(
            BACKEND_URL,
            data=ujson.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=POST_TIMEOUT
        )
        ok = (resp.status_code == 200)
        resp.close()   #frees the socket; skipping this leaks RAM
        return ok
    except Exception as e:
        print("POST failed:", e)
        return False


# ─── buffer ───────────────────────────

buffer = []

def queue_reading(payload):
    buffer.append(payload)
    if len(buffer) > MAX_BUFFER:
        buffer.pop(0)   #drop oldest to make room for more recent data

def flush_buffer():
    while buffer:
        if send_reading(buffer[0]):
            buffer.pop(0)
        else:
            break   #still no connectivity, stop trying until next cycle


# ─── main ────────────────────────────────────────

pms = PMS5003()
boot_time = time.time()

# initial WiFi + time sync
if connect_wifi():
    sync_time()

while True:
    # reconnect if WiFi dropped
    if not network.WLAN(network.STA_IF).isconnected():
        connect_wifi()

    # skip PMS5003 reads during warm-up window
    if time.time() - boot_time < WARMUP_SECONDS:
        print("Warming up, waiting for PMS5003 to stabilise...")
        time.sleep(READ_INTERVAL)
        continue

    pm_result = pms.read()
    temp, hum = read_dht22()

    # only send if we have valid PM data; DHT22 can be None and we still send
    if pm_result is not None:
        pm25, pm10 = pm_result
        payload = {
            "device_id":   DEVICE_ID,
            "recorded_at": unix_timestamp(),
            "pm25":        pm25,
            "pm10":        pm10,
            "temperature": temp,
            "humidity":    hum,
        }
        print("Reading:", payload)

        if network.WLAN(network.STA_IF).isconnected():
            if send_reading(payload):
                flush_buffer()       #clear any backlog while we have connectivity
            else:
                queue_reading(payload)
        else:
            queue_reading(payload)
    else:
        print("No valid PMS5003 frame this cycle, skipping.")

    time.sleep(READ_INTERVAL)