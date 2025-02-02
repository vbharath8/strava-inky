"""
Code used in main.py on inky frame
"""
import gc
import jpegdec
import ntptime
import time
import inky_frame
import network
from urllib import urequest
from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7 as DISPLAY
from secrets import WIFI_SSID, WIFI_PASSWORD

# 🔹 Image URLs
IMAGE_1_URL = "https://vbharath8.github.io/strava-inky/combined_summary.jpg"
IMAGE_2_URL = "https://vbharath8.github.io/strava-inky/race_calendar.jpg"

# 🔹 File paths in internal flash (since no SD card is used)
IMAGE_1_PATH = "/combined_summary.jpg"
IMAGE_2_PATH = "/race_calendar.jpg"

# 🔹 Update schedule
UPDATE_INTERVAL = 15 * 60  # 15 minutes in seconds
SLEEP_START_HOUR = 22  # 10 PM ET
SLEEP_END_HOUR = 7  # 7 AM ET
ET_OFFSET = -5 * 3600  # Convert UTC to Eastern Time (ET = UTC-5)

# 🔹 Initialize Inky Frame Display
graphics = PicoGraphics(display=DISPLAY)
graphics.set_pen(1)
graphics.clear()


# 🔹 Connect to Wi-Fi on Startup
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(10):  # Wait up to 10 seconds for connection
            if wlan.isconnected():
                break
            time.sleep(1)

    if not wlan.isconnected():
        print("Wi-Fi connection failed! Sleeping for 15 minutes.")
        inky_frame.sleep_for(UPDATE_INTERVAL)  # Sleep and retry later
        exit()


connect_wifi()  # Ensure Wi-Fi is connected before downloading images


# Sync Time with NTP (Internet Time)
def get_current_hour_et():
    """Gets the current hour in Eastern Time (ET)."""
    try:
        ntptime.settime()  # Sync system time to UTC
        return time.localtime(time.time() + ET_OFFSET)[3]  # Convert to ET, return hour
    except:
        return -1  # Invalid time if sync fails


# 🔹 Download Image to Internal Flash
def download_image(url, save_path):
    """Downloads an image from a URL and saves it to flash memory."""
    try:
        socket = urequest.urlopen(url)
        with open(save_path, "wb") as f:
            while True:
                chunk = socket.read(1024)  # Read 1KB chunks
                if not chunk:
                    break
                f.write(chunk)
        socket.close()
        return True
    except:
        return False


# 🔹 Display Image from Flash Storage
def draw_image(image_path):
    """Displays an image from internal flash storage."""
    try:
        gc.collect()
        jpeg = jpegdec.JPEG(graphics)
        graphics.set_pen(1)
        graphics.clear()
        jpeg.open_file(image_path)
        jpeg.decode()
        graphics.update()
    except:
        pass


# 🔹 Determine which image to display (toggle between two)
try:
    with open("/last_image.txt", "r") as f:
        last_image = int(f.read().strip())  # Read the last displayed image
except:
    last_image = 1  # Default to IMAGE_1 if file doesn't exist

# 🔹 Get current time in ET
current_hour_et = get_current_hour_et()

# 🔹 Skip updates during 10 PM - 7 AM ET (deep sleep until 7 AM)
if current_hour_et != -1 and (SLEEP_START_HOUR <= current_hour_et or current_hour_et < SLEEP_END_HOUR):
    inky_frame.sleep_until(7, 0, 0)  # Wake up at 7:00 AM ET
    exit()

# 🔹 Swap and display the next image
if last_image == 1:
    if download_image(IMAGE_1_URL, IMAGE_1_PATH):
        draw_image(IMAGE_1_PATH)
        last_image = 2
else:
    if download_image(IMAGE_2_URL, IMAGE_2_PATH):
        draw_image(IMAGE_2_PATH)
        last_image = 1

# 🔹 Save last displayed image index
with open("/last_image.txt", "w") as f:
    f.write(str(last_image))

# 🔹 Go into deep sleep for 15 minutes
inky_frame.sleep_for(UPDATE_INTERVAL)
