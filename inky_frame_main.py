#############################################################
# code in main.py on Inky Frame
############################################################

import gc
import ntptime
import time
import network
import inky_frame
from urllib import urequest
from picographics import PicoGraphics, DISPLAY_INKY_FRAME_7 as DISPLAY
from secrets import WIFI_SSID, WIFI_PASSWORD

# ----------------------------
# Configuration
# ----------------------------
# URLs of the two images to toggle
IMAGE_1_URL = "https://vbharath8.github.io/strava-inky/combined_summary.jpg"
IMAGE_2_URL = "https://vbharath8.github.io/strava-inky/race_calendar.jpg"

# Paths in internal flash to save them
IMAGE_1_PATH = "/combined_summary.jpg"
IMAGE_2_PATH = "/race_calendar.jpg"

# Times in 24-hour for skipping
SLEEP_START_HOUR = 21  # 9 PM
SLEEP_END_HOUR   = 8   # 8 AM

# For Eastern Time, set offset from UTC
# If currently EST (UTC-5), use -5*3600
# If currently EDT (UTC-4), use -4*3600
ET_OFFSET = -5 * 3600

# How often to refresh (minutes)
UPDATE_INTERVAL = 15

# File to remember which image was shown last
LAST_IMAGE_FILE = "/last_image.txt"

# ----------------------------
# Set up the display
# ----------------------------
graphics = PicoGraphics(display=DISPLAY)
graphics.set_pen(1)
graphics.clear()
graphics.update()

# ----------------------------
# Connect to Wi-Fi
# ----------------------------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for attempt in range(10):  # Wait up to ~30 seconds
            if wlan.isconnected():
                break
            print(f"  Attempt {attempt+1}/30...")
            time.sleep(3)

    if wlan.isconnected():
        print("Wi-Fi connected:", wlan.ifconfig())
        return True
    else:
        print("Wi-Fi failed to connect!")
        return False

# ----------------------------
# NTP / get current ET hour
# ----------------------------
def get_current_hour_et():
    try:
        ntptime.settime()  # This sets device time to UTC
        # Local system time (UTC) plus ET_OFFSET
        t = time.localtime(time.time() + ET_OFFSET)
        current_hour = t[3]
        print("UTC now =", time.localtime())
        print("ET now  =", t)
        return current_hour
    except Exception as e:
        print("NTP sync failed:", e)
        # Return -1 to indicate we don't have a valid time
        return -1

# ----------------------------
# Download an image
# ----------------------------
def download_image(url, save_path):
    try:
        print(f"Downloading from: {url}")
        socket = urequest.urlopen(url)
        with open(save_path, "wb") as f:
            while True:
                chunk = socket.read(1024)
                if not chunk:
                    break
                f.write(chunk)
        socket.close()
        print(f"Saved image to {save_path}")
        return True
    except Exception as e:
        print("Error downloading image:", e)
        return False

# ----------------------------
# Display an image
# ----------------------------
def draw_image(path):
    try:
        gc.collect()
        import jpegdec
        jpeg = jpegdec.JPEG(graphics)
        graphics.set_pen(1)
        graphics.clear()
        jpeg.open_file(path)
        jpeg.decode()
        graphics.update()
        print(f"Displayed image: {path}")
    except Exception as e:
        print("Error displaying image:", e)

# ----------------------------
# Main logic
# ----------------------------
def main():
    # Attempt Wi-Fi so we can NTP sync
    if not connect_wifi():
        # If Wi-Fi fails entirely, just sleep and try again
        print("Sleeping 15 min, then retry Wi-Fi...")
        inky_frame.sleep_for(UPDATE_INTERVAL)
        return

    # Now get current ET hour from NTP
    current_hour_et = get_current_hour_et()
    if current_hour_et == -1:
        # If we failed to get valid time, we can't do time-based skipping
        print("Skipping NTP-based sleep. Will just toggle image.")
    else:
        # If we have a valid time, check if it's within the skip window
        # 9 PM <= hour < 24, or 0 <= hour < 8 AM
        if current_hour_et >= SLEEP_START_HOUR or current_hour_et < SLEEP_END_HOUR:
            # It's within the 9 PM–8 AM window
            print("Within the 9 PM–8 AM window, sleeping until 8 AM...")
            # Calculate how many hours until 8 AM
            # If it's 21 (9 PM), we want to sleep 11 hours until 8 AM.
            # If it's 23 (11 PM), we want to sleep 9 hours, etc.
            # If it's 0, we sleep 8 hours, and so forth.
            hours_until_8 = 0
            if current_hour_et >= SLEEP_START_HOUR:
                # e.g. 21 (9 PM) => 21->24 is 3 hours, plus 8 more => 11 hours total
                hours_until_8 = (24 - current_hour_et) + SLEEP_END_HOUR
            else:
                # e.g. if hour is 2, then we just need 6 hours until 8
                hours_until_8 = SLEEP_END_HOUR - current_hour_et

            minutes_until_8 = hours_until_8 * 60
            print(f"Sleeping {minutes_until_8} minutes (until ~8 AM ET).")
            inky_frame.sleep_for(minutes_until_8)
            return

    # Now we toggle the image
    try:
        with open(LAST_IMAGE_FILE, "r") as f:
            last_image = int(f.read().strip())
    except:
        last_image = 1  # Default if file doesn't exist

    if last_image == 1:
        print("Displaying Image 1...")
        if download_image(IMAGE_1_URL, IMAGE_1_PATH):
            draw_image(IMAGE_1_PATH)
            last_image = 2
    else:
        print("Displaying Image 2...")
        if download_image(IMAGE_2_URL, IMAGE_2_PATH):
            draw_image(IMAGE_2_PATH)
            last_image = 1

    # Save which image we displayed
    with open(LAST_IMAGE_FILE, "w") as f:
        f.write(str(last_image))

    # Finally, sleep for 15 minutes
    print(f"Now sleeping for {UPDATE_INTERVAL} minutes...\n")
    inky_frame.sleep_for(UPDATE_INTERVAL)

# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    main()

