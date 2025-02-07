#!/usr/bin/env python3
# NoiseBuster - created by Raphaël Vael (Main Dev)
# License: CC BY-NC 4.0
#
# Changelog:
#   - [Original Versions] Raphaël Vael
#   - [Mark Deneen] Improved MQTT support
#   - [Alexander Koch] Added serial device support
#   - [lruppert] Docker + TLS option for MQTT
#   - [Current Merge] Fix MQTT deprecation warning, fallback from Serial to USB

import sys
import os
import logging
import json
import time
import traceback
from datetime import datetime, timedelta, timezone
import threading
from queue import Queue
import socket
import urllib.parse
import http.client

# Required modules for USB-based sound meter and scheduling
required_modules = [
    'usb.core',
    'usb.util',
    'requests',
    'schedule',
]

# Attempt to import these mandatory modules
missing_modules = []
for module in required_modules:
    try:
        __import__(module)
    except ImportError:
        missing_modules.append(module)

if missing_modules:
    print("The following required modules are missing:")
    for module in missing_modules:
        print(f"- {module}")
    print("\nPlease install them by running:")
    print(f"pip install {' '.join(missing_modules)}")
    sys.exit(1)

# Now actually import them
import usb.core
import usb.util
import requests
import schedule

# We will try to import serial (for Alexander's feature)
try:
    import serial
except ImportError:
    serial = None

# We'll keep optional modules as None if not installed or not enabled
InfluxDBClient = None
SYNCHRONOUS = None
mqtt = None
cv2 = None
np = None

# Load config from config.json
def load_config(config_path):
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    return config

try:
    config = load_config('config.json')
except json.JSONDecodeError as e:
    print(f"Error parsing config.json: {e}")
    sys.exit(1)
except FileNotFoundError as e:
    print(f"Configuration file not found: {e}")
    sys.exit(1)

# Extract main sections of the config
INFLUXDB_CONFIG = config.get("INFLUXDB_CONFIG", {})
PUSHOVER_CONFIG = config.get("PUSHOVER_CONFIG", {})
WEATHER_CONFIG = config.get("WEATHER_CONFIG", {})
MQTT_CONFIG = config.get("MQTT_CONFIG", {})
CAMERA_CONFIG = config.get("CAMERA_CONFIG", {})
IMAGE_STORAGE_CONFIG = config.get("IMAGE_STORAGE_CONFIG", {})
DEVICE_AND_NOISE_MONITORING_CONFIG = config.get("DEVICE_AND_NOISE_MONITORING_CONFIG", {})
TELRAAM_API_CONFIG = config.get("TELRAAM_API_CONFIG", {})
TIMEZONE_CONFIG = config.get("TIMEZONE_CONFIG", {})
DISCORD_CONFIG = config.get("DISCORD_CONFIG", {})

# For serial usage
SERIAL_CONFIG = config.get("SERIAL_CONFIG", {})
use_serial_device = SERIAL_CONFIG.get("enabled", False)

# Retrieve USB device IDs from the config
usb_vendor_id_str = DEVICE_AND_NOISE_MONITORING_CONFIG.get("usb_vendor_id", "")
usb_product_id_str = DEVICE_AND_NOISE_MONITORING_CONFIG.get("usb_product_id", "")

usb_vendor_id_int = int(usb_vendor_id_str, 16) if usb_vendor_id_str else None
usb_product_id_int = int(usb_product_id_str, 16) if usb_product_id_str else None

####################################
# LOGGING CONFIGURATION
####################################
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[37m',    # White
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m', # Red background
    }
    RESET = '\033[0m'
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
console_formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(console_formatter)
logger.addHandler(ch)

# File handler: only add if LOCAL_LOGGING is enabled in config
if config.get("LOCAL_LOGGING", True):
    fh = logging.FileHandler('noisebuster.log')
    fh.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(file_formatter)
    logger.addHandler(fh)
    logger.info("Detailed logs are saved in 'noisebuster.log'.")
else:
    logger.info("Local logging has been disabled in config.json.")

####################################
# LOAD USB IDs
####################################
def load_usb_ids(usb_ids_path):
    usb_ids = []
    try:
        with open(usb_ids_path, 'r') as usb_ids_file:
            for line in usb_ids_file:
                # remove comments
                line_content, sep, comment = line.partition('#')
                line_content = line_content.strip()
                if not line_content:
                    continue
                parts = line_content.split(',')
                if len(parts) >= 2:
                    vendor_id_str, product_id_str = parts[0], parts[1]
                    model = comment.strip() if comment else "Unknown model"
                    vendor_id = int(vendor_id_str, 16)
                    product_id = int(product_id_str, 16)
                    usb_ids.append((vendor_id, product_id, model))
                else:
                    logger.warning(f"Incorrect format in USB IDs file: {line.strip()}")
    except FileNotFoundError:
        logger.warning(f"USB IDs file '{usb_ids_path}' not found. Automatic detection may fail.")
    return usb_ids

usb_ids = load_usb_ids('usb_ids')

####################################
# IMPORT OPTIONAL MODULES
####################################
def import_optional_modules():
    global InfluxDBClient, SYNCHRONOUS, mqtt, cv2, np
    missing_optional_modules = []

    # Influx
    if INFLUXDB_CONFIG.get("enabled"):
        try:
            from influxdb_client import InfluxDBClient as InfluxDBClientImported
            from influxdb_client.client.write_api import SYNCHRONOUS as SYNCHRONOUS_IMPORTED
            InfluxDBClient = InfluxDBClientImported
            SYNCHRONOUS = SYNCHRONOUS_IMPORTED
        except ImportError:
            logger.error("InfluxDB client library not installed ('influxdb-client').")
            missing_optional_modules.append('influxdb_client')

    # MQTT
    if MQTT_CONFIG.get("enabled"):
        try:
            import paho.mqtt.client as mqtt_imported
            mqtt = mqtt_imported
        except ImportError:
            logger.error("MQTT client library 'paho-mqtt' not installed.")
            missing_optional_modules.append('paho-mqtt')

    # Camera
    if CAMERA_CONFIG.get("use_ip_camera"):
        try:
            import cv2 as cv2_imported
            import numpy as np_imported
            cv2 = cv2_imported
            np = np_imported
        except ImportError:
            logger.error("OpenCV or numpy not installed. Please install 'opencv-python' + 'numpy'.")
            missing_optional_modules.append('opencv-python, numpy')

    return missing_optional_modules

missing_optional_modules = import_optional_modules()

####################################
# CONFIGURATION VALIDATION
####################################
def check_configuration():
    logger.info("Checking configuration...")

    # InfluxDB
    if INFLUXDB_CONFIG.get("enabled"):
        influxdb_missing = []
        required_fields = ["host", "port", "token", "org", "bucket", "realtime_bucket"]
        for field in required_fields:
            if not INFLUXDB_CONFIG.get(field) or str(INFLUXDB_CONFIG.get(field)).startswith("<YOUR_"):
                influxdb_missing.append(field)
        bucket_name = INFLUXDB_CONFIG.get("bucket","")
        realtime_bucket_name = INFLUXDB_CONFIG.get("realtime_bucket","")
        if bucket_name != "noise_buster":
            logger.error("InfluxDB 'bucket' must be 'noise_buster'.")
            influxdb_missing.append('bucket')
        if realtime_bucket_name != "noise_buster_realtime":
            logger.error("InfluxDB 'realtime_bucket' must be 'noise_buster_realtime'.")
            influxdb_missing.append('realtime_bucket')
        if influxdb_missing:
            logger.error(f"InfluxDB is missing or misconfigured: {', '.join(influxdb_missing)}. Disabling.")
            INFLUXDB_CONFIG["enabled"] = False
        else:
            logger.info("InfluxDB is enabled and properly configured.")
    else:
        logger.info("InfluxDB is disabled.")

    # Pushover
    if PUSHOVER_CONFIG.get("enabled"):
        needed_fields = ["user_key", "api_token"]
        missing = [f for f in needed_fields if not PUSHOVER_CONFIG.get(f) or PUSHOVER_CONFIG[f].startswith("<YOUR_")]
        if missing:
            logger.error(f"Pushover is enabled but missing: {', '.join(missing)}. Disabling.")
            PUSHOVER_CONFIG["enabled"] = False
        else:
            logger.info("Pushover is enabled and properly configured.")
    else:
        logger.info("Pushover is disabled.")

    # Weather
    if WEATHER_CONFIG.get("enabled"):
        needed_fields = ["api_key", "api_url", "location"]
        missing = [f for f in needed_fields if not WEATHER_CONFIG.get(f) or WEATHER_CONFIG[f].startswith("<YOUR_")]
        if missing:
            logger.error(f"Weather enabled but missing: {', '.join(missing)}. Disabling.")
            WEATHER_CONFIG["enabled"] = False
        else:
            logger.info("Weather data collection is enabled.")
    else:
        logger.info("Weather data collection is disabled.")

    # MQTT
    if MQTT_CONFIG.get("enabled"):
        needed_fields = ["server", "port"]
        missing = [f for f in needed_fields if not MQTT_CONFIG.get(f)]
        if missing:
            logger.error(f"MQTT missing: {', '.join(missing)}. Disabling.")
            MQTT_CONFIG["enabled"] = False
        else:
            logger.info("MQTT is enabled and properly configured.")
    else:
        logger.info("MQTT is disabled.")

    # Camera
    if CAMERA_CONFIG.get("use_ip_camera"):
        needed_fields = ["ip_camera_url", "ip_camera_protocol"]
        missing = [f for f in needed_fields if not CAMERA_CONFIG.get(f)]
        if missing:
            logger.error(f"IP Camera missing: {', '.join(missing)}. Disabling.")
            CAMERA_CONFIG["use_ip_camera"] = False
        else:
            logger.info("IP camera is enabled.")
    else:
        logger.info("IP camera is disabled.")

    # Telraam
    if TELRAAM_API_CONFIG.get("enabled"):
        needed_fields = ["api_key", "segment_id"]
        missing = [f for f in needed_fields if not TELRAAM_API_CONFIG.get(f) or TELRAAM_API_CONFIG[f].startswith("<YOUR_")]
        if missing:
            logger.error(f"Telraam missing: {', '.join(missing)}. Disabling.")
            TELRAAM_API_CONFIG["enabled"] = False
        else:
            logger.info("Telraam data collection is enabled.")
    else:
        logger.info("Telraam is disabled.")

    # Discord
    if DISCORD_CONFIG.get("enabled"):
        needed_fields = ["webhook_url"]
        missing = [f for f in needed_fields if not DISCORD_CONFIG.get(f) or DISCORD_CONFIG[f].startswith("<YOUR_")]
        if missing:
            logger.error(f"Discord missing: {', '.join(missing)}. Disabling.")
            DISCORD_CONFIG["enabled"] = False
        else:
            logger.info("Discord notifications are enabled.")
    else:
        logger.info("Discord is disabled.")

    # Device & Noise
    if not DEVICE_AND_NOISE_MONITORING_CONFIG.get("minimum_noise_level"):
        logger.error("No 'minimum_noise_level' in DEVICE_AND_NOISE_MONITORING_CONFIG.")
    else:
        logger.info(f"Minimum noise level: {DEVICE_AND_NOISE_MONITORING_CONFIG['minimum_noise_level']} dB.")

check_configuration()

####################################
# USB / SERIAL DETECTION
####################################
device_detected = False

def detect_usb_device(verbose=True):
    global device_detected
    devs = usb.core.find(find_all=True)
    for dev in devs:
        dev_vendor_id = dev.idVendor
        dev_product_id = dev.idProduct

        # If config specifically sets vendor/product
        if usb_vendor_id_int and usb_product_id_int:
            if dev_vendor_id == usb_vendor_id_int and dev_product_id == usb_product_id_int:
                if verbose or not device_detected:
                    model = next((name for vid, pid, name in usb_ids
                                  if vid == dev_vendor_id and pid == dev_product_id), None)
                    if model:
                        logger.info(f"Detected specified device: {model} (Vendor {hex(dev_vendor_id)}, Product {hex(dev_product_id)})")
                    else:
                        logger.info("User-defined USB sound device detected (not in usb_ids list).")
                device_detected = True
                return dev
        else:
            # If not specifically set, check the usb_ids file
            known = next((m for m in usb_ids if m[0] == dev_vendor_id and m[1] == dev_product_id), None)
            if known:
                if verbose or not device_detected:
                    logger.info(f"{known[2]} sound meter detected (Vendor {hex(dev_vendor_id)}, Product {hex(dev_product_id)})")
                device_detected = True
                return dev
            else:
                if verbose and not device_detected:
                    logger.info(f"Ignoring device: Vendor {hex(dev_vendor_id)}, Product {hex(dev_product_id)}")

    # No device found
    device_detected = False
    if usb_vendor_id_int and usb_product_id_int:
        logger.error("Specified USB device not found. Check config or cable.")
    else:
        logger.error("No known USB sound meter found. Possibly not connected?")
    return None

def detect_serial_device(verbose=True):
    """Attempt to open a serial device as configured in SERIAL_CONFIG."""
    if not serial:
        logger.warning("PySerial not installed, can't use serial device.")
        return None
    if not SERIAL_CONFIG.get("enabled"):
        return None
    port = SERIAL_CONFIG.get("port", "/dev/ttyUSB0")
    baud = SERIAL_CONFIG.get("baudrate", 115200)
    try:
        ser = serial.Serial(port=port, baudrate=baud, timeout=1)
        if verbose:
            logger.info(f"Serial device connected on {port} at {baud} baud.")
        return ser
    except serial.SerialException as e:
        logger.error(f"Could not open serial port {port}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error opening serial port {port}: {str(e)}")
        return None

####################################
# INFLUXDB
####################################
failed_writes_queue = Queue()
InfluxDB_CLIENT = None
write_api = None

def connect_influxdb():
    if INFLUXDB_CONFIG.get("enabled") and InfluxDBClient:
        try:
            protocol = "https" if INFLUXDB_CONFIG.get("ssl") else "http"
            c = InfluxDBClient(
                url=f"{protocol}://{INFLUXDB_CONFIG['host']}:{INFLUXDB_CONFIG['port']}",
                token=INFLUXDB_CONFIG['token'],
                org=INFLUXDB_CONFIG['org'],
                timeout=INFLUXDB_CONFIG.get('timeout', 20000)
            )
            w_api = c.write_api(write_options=SYNCHRONOUS)
            return c, w_api
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            INFLUXDB_CONFIG["enabled"] = False
            return None, None
    else:
        return None, None

InfluxDB_CLIENT, write_api = connect_influxdb()

####################################
# MQTT
####################################
mqtt_client = None
mqtt_connected = False
if MQTT_CONFIG.get("enabled") and mqtt:
    # Use MQTTv5 to avoid the v1 callback warning
    mqtt_client = mqtt.Client(protocol=mqtt.MQTTv5)
    if MQTT_CONFIG.get("tls"):
        try:
            mqtt_client.tls_set()  # If you need to set specific certs, do it here
            # mqtt_client.tls_insecure_set(True) if needed for self-signed
            logger.info("MQTT TLS enabled.")
        except Exception as e:
            logger.error(f"Failed to set up MQTT TLS: {str(e)}")

    if MQTT_CONFIG.get("user") and MQTT_CONFIG.get("password"):
        mqtt_client.username_pw_set(MQTT_CONFIG["user"], MQTT_CONFIG["password"])

    try:
        availability_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/noise_level/availability"
        mqtt_client.will_set(availability_topic, payload="offline", qos=1, retain=True)
        mqtt_client.connect(MQTT_CONFIG["server"], MQTT_CONFIG["port"], 60)
        mqtt_client.loop_start()

        # Publish sensor config
        def publish_sensor_config():
            noise_sensor_config = {
                "device_class": "sound_pressure",
                "name": f"{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']} Noise Level",
                "state_topic": f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/realtime_noise_levels/state",
                "unit_of_measurement": "dB",
                "value_template": "{{ value_json.noise_level }}",
                "unique_id": f"{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}_noise_level_sensor",
                "availability_topic": availability_topic,
                "device": {
                    "identifiers": [f"{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}_sensor"],
                    "name": f"{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']} Noise Sensor",
                    "model": "Custom Noise Sensor",
                    "manufacturer": "Silkyclouds"
                }
            }
            config_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/noise_level/config"
            mqtt_client.publish(config_topic, json.dumps(noise_sensor_config), qos=1, retain=True)
            logger.info(f"Sensor config published to {config_topic}")
            mqtt_client.publish(availability_topic, "online", qos=1, retain=True)
            logger.info(f"Sensor availability published to {availability_topic}")

        def on_connect(client, userdata, flags, reasonCode, properties=None):
            if reasonCode == 0:
                logger.info("MQTT client connected successfully.")
                publish_sensor_config()
            else:
                logger.info("MQTT disconnected.")
        mqtt_client.on_connect = on_connect
        mqtt_connected = True
#        publish_sensor_config()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {str(e)}")
        MQTT_CONFIG["enabled"] = False
else:
    if MQTT_CONFIG.get("enabled") and not mqtt:
        logger.error("MQTT is enabled but paho-mqtt is not installed. Disabling.")
        MQTT_CONFIG["enabled"] = False

####################################
# DISCORD
####################################
def send_discord_notification(message):
    if DISCORD_CONFIG.get("enabled"):
        wh = DISCORD_CONFIG.get("webhook_url")
        if wh and not wh.startswith("<YOUR_"):
            try:
                resp = requests.post(wh, json={"content": message})
                if resp.status_code == 204:
                    logger.info("Discord notification sent.")
                else:
                    logger.error(f"Failed to send Discord notification: {resp.status_code}, {resp.text}")
            except Exception as e:
                logger.error(f"Error sending Discord notification: {str(e)}")
                logger.debug("Exception details:", exc_info=True)
        else:
            logger.error("Discord webhook URL is missing or invalid. Disabling.")
            DISCORD_CONFIG["enabled"] = False

####################################
# PUSHOVER
####################################
def send_pushover_notification(message):
    if PUSHOVER_CONFIG.get("enabled"):
        if PUSHOVER_CONFIG.get("user_key") and PUSHOVER_CONFIG.get("api_token"):
            try:
                conn = http.client.HTTPSConnection("api.pushover.net:443")
                conn.request("POST", "/1/messages.json",
                             urllib.parse.urlencode({
                                 "token": PUSHOVER_CONFIG["api_token"],
                                 "user": PUSHOVER_CONFIG["user_key"],
                                 "message": message,
                                 "title": PUSHOVER_CONFIG.get("title", "Noise Buster")
                             }), {"Content-type": "application/x-www-form-urlencoded"})
                conn.getresponse()
                logger.info(f"Pushover notification sent: {message}")
            except Exception as e:
                logger.error(f"Error sending Pushover notification: {str(e)}")
        else:
            logger.error("Pushover user_key or api_token missing. Disabling.")
            PUSHOVER_CONFIG["enabled"] = False

####################################
# MQTT PUBLISH
####################################
def send_to_mqtt(topic, payload):
    if mqtt_client and MQTT_CONFIG.get("enabled"):
        mqtt_client.publish(topic, payload)
        logger.info(f"Data published to MQTT: {topic} -> {payload}")

####################################
# CAMERA
####################################
def capture_image(current_peak_dB, peak_temperature, peak_weather_description, peak_precipitation, timestamp):
    if CAMERA_CONFIG.get("use_ip_camera"):
        if cv2 is None:
            logger.error("OpenCV not installed. Can't capture images.")
            return
        cap = cv2.VideoCapture(CAMERA_CONFIG["ip_camera_url"])
        ret, frame = cap.read()
        cap.release()
    else:
        logger.debug("IP camera usage not configured.")
        return

    if frame is not None:
        formatted_time = timestamp.strftime("%Y-%m-%d_%H:%M:%S")
        weather_info = f"{peak_weather_description.replace(' ', '_')}_{peak_temperature}C"
        filename = f"{formatted_time}_{weather_info}.jpg"
        filepath = os.path.join(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path'], filename)

        if not os.path.exists(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path']):
            os.makedirs(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path'])
            logger.info(f"Created directory: {DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path']}")

        text_lines = [
            f"Time: {formatted_time}",
            f"Noise: {current_peak_dB} dB",
            f"Temp: {peak_temperature} C",
            f"Weather: {peak_weather_description}",
            f"Precipitation: {peak_precipitation} mm"
        ]
        y_position = 50
        for line in text_lines:
            cv2.putText(frame, line, (10, y_position), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            y_position += 30
        cv2.imwrite(filepath, frame)
        logger.info(f"Image saved: {filepath}")

def delete_old_images():
    image_path = DEVICE_AND_NOISE_MONITORING_CONFIG.get('image_save_path', './images')
    if not os.path.exists(image_path):
        os.makedirs(image_path)
        logger.info(f"Created image directory: {image_path}")

    current_time = datetime.now()
    retention_hours = DEVICE_AND_NOISE_MONITORING_CONFIG.get('image_retention_hours', 24)
    for filename in os.listdir(image_path):
        filepath = os.path.join(image_path, filename)
        if os.path.isfile(filepath):
            file_creation_time = datetime.fromtimestamp(os.path.getctime(filepath))
            time_diff = current_time - file_creation_time
            if time_diff > timedelta(hours=retention_hours):
                os.remove(filepath)
                logger.info(f"Deleted old image: {filepath}")

####################################
# WEATHER
####################################
def get_weather():
    if not WEATHER_CONFIG.get("enabled"):
        return None, None, 0.0
    try:
        resp = requests.get(
            f"{WEATHER_CONFIG['api_url']}?q={WEATHER_CONFIG['location']}&appid={WEATHER_CONFIG['api_key']}&units=metric"
        )
        resp.raise_for_status()
        data = resp.json()
        temperature = float(data['main']['temp'])
        weather_description = data['weather'][0]['description']
        precipitation_float = 0.0
        if 'rain' in data and '1h' in data['rain']:
            precipitation_float += float(data['rain']['1h'])
        if 'snow' in data and '1h' in data['snow']:
            precipitation_float += float(data['snow']['1h'])
        return temperature, weather_description, precipitation_float
    except Exception as e:
        logger.error(f"Failed to get weather data: {str(e)}")
        return None, None, 0.0

####################################
# MAIN NOISE MONITOR
####################################
def update_noise_level():
    """Monitor noise from either Serial or USB, record events, and publish/log them."""
    window_start_time = time.time()
    current_peak_dB = 0
    peak_temperature = None
    peak_weather_description = ""
    peak_precipitation_float = 0.0

    # Attempt to open Serial if enabled
    ser_dev = None
    usb_dev = None
    if use_serial_device:
        ser_dev = detect_serial_device(verbose=True)
        if not ser_dev:
            logger.warning("Serial device not found - falling back to USB.")
            usb_dev = detect_usb_device(verbose=True)
            if not usb_dev:
                logger.error("No USB fallback device found. Exiting.")
                sys.exit(1)
        else:
            logger.info("Noise monitoring on Serial device.")
    else:
        usb_dev = detect_usb_device(verbose=True)
        if not usb_dev:
            logger.error("No USB device found (Serial is disabled). Exiting.")
            sys.exit(1)
        logger.info("Noise monitoring on USB device.")

    while True:
        current_time = time.time()
        if (current_time - window_start_time) >= DEVICE_AND_NOISE_MONITORING_CONFIG['time_window_duration']:
            timestamp = datetime.utcnow()
            delete_old_images()
            logger.info(f"Time window elapsed. Current peak dB: {round(current_peak_dB, 1)}")

            # Realtime data
            realtime_data = [{
                "measurement": "noise_buster_events",
                "tags": {"location": "noise_buster"},
                "time": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": {
                    "noise_level": round(current_peak_dB, 1)
                }
            }]

            logger.info(f"Current noise level: {round(current_peak_dB, 1)} dB")

            # Influx DB (realtime bucket)
            if INFLUXDB_CONFIG.get("enabled") and InfluxDB_CLIENT and write_api:
                try:
                    write_api.write(bucket=INFLUXDB_CONFIG['realtime_bucket'], record=realtime_data)
                    logger.info(f"All noise levels written to realtime bucket: {round(current_peak_dB, 1)} dB")
                except Exception as e:
                    logger.error(f"Failed to write to InfluxDB: {str(e)}. Queueing.")
                    failed_writes_queue.put((INFLUXDB_CONFIG['realtime_bucket'], [realtime_data]))

            # MQTT (realtime)
            if mqtt_client and MQTT_CONFIG.get("enabled"):
                realtime_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/realtime_noise_levels/state"
                realtime_payload = json.dumps(realtime_data[0]['fields'])
                send_to_mqtt(realtime_topic, realtime_payload)

            # If above threshold
            if current_peak_dB >= DEVICE_AND_NOISE_MONITORING_CONFIG['minimum_noise_level']:
                peak_temp_float = float(peak_temperature) if peak_temperature else 0.0
                peak_weather_desc = peak_weather_description if peak_weather_description else ""
                main_data = {
                    "measurement": "noise_buster_events",
                    "tags": {"location": "noise_buster"},
                    "time": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "fields": {
                        "noise_level": round(current_peak_dB, 1),
                        "temperature": peak_temp_float,
                        "weather_description": peak_weather_desc,
                        "precipitation": peak_precipitation_float
                    }
                }

                logger.info(f"Noise level exceeded threshold: {round(current_peak_dB, 1)} dB")

                # Influx DB main bucket
                if INFLUXDB_CONFIG.get("enabled") and InfluxDB_CLIENT and write_api:
                    try:
                        write_api.write(bucket=INFLUXDB_CONFIG['bucket'], record=main_data)
                        logger.info(f"High noise level data written to main bucket: {main_data}")
                    except Exception as e:
                        logger.error(f"Failed to write main data to InfluxDB: {str(e)}. Queueing.")
                        failed_writes_queue.put((INFLUXDB_CONFIG['bucket'], [main_data]))

                # MQTT event
                if mqtt_client and MQTT_CONFIG.get("enabled"):
                    event_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/noise_levels/state"
                    event_payload = json.dumps(main_data['fields'])
                    send_to_mqtt(event_topic, event_payload)

                # Camera
                capture_image(current_peak_dB, peak_temp_float, peak_weather_desc, peak_precipitation_float, timestamp)

            # reset
            window_start_time = current_time
            current_peak_dB = 0
            peak_temperature = None
            peak_weather_description = ""
            peak_precipitation_float = 0.0

        # Reading from device
        try:
            if ser_dev:
                line = ser_dev.readline().decode().strip()
                if line:
                    dB = float(line)
                    if dB > current_peak_dB:
                        current_peak_dB = dB
                        if WEATHER_CONFIG.get("enabled"):
                            peak_temperature, peak_weather_description, p = get_weather()
                            peak_precipitation_float = float(p)
            elif usb_dev:
                ret = usb_dev.ctrl_transfer(0xC0, 4, 0, 0, 200)
                dB = (ret[0] + ((ret[1] & 3) * 256)) * 0.1 + 30
                dB = round(dB, 1)
                if dB > current_peak_dB:
                    current_peak_dB = dB
                    if WEATHER_CONFIG.get("enabled"):
                        peak_temperature, peak_weather_description, p = get_weather()
                        peak_precipitation_float = float(p)
            else:
                logger.error("No device found (neither USB nor Serial). Breaking loop.")
                break
        except usb.core.USBError as usb_err:
            logger.error(f"USB Error reading: {str(usb_err)}")
            usb_dev = detect_usb_device(verbose=False)
            if not usb_dev:
                logger.error("Device not found on re-scan.")
            else:
                logger.info("Reconnected to USB device.")
        except Exception as e:
            logger.error(f"Unexpected error reading from device: {str(e)}")

        time.sleep(0.1)

####################################
# SCHEDULING
####################################
def schedule_tasks():
    try:
        # Telraam
        if TELRAAM_API_CONFIG.get("enabled"):
            interval = TELRAAM_API_CONFIG["request_interval_minutes"]
            schedule.every(interval).minutes.do(update_traffic_data)
            logger.info(f"Telraam tasks scheduled every {interval} minutes.")

        # Weather
        if WEATHER_CONFIG.get("enabled"):
            schedule.every(5).minutes.do(update_weather_data)
            logger.info("Weather data scheduled every 5 minutes.")

        # Influx retries
        if INFLUXDB_CONFIG.get("enabled"):
            schedule.every(1).minutes.do(retry_failed_writes)
    except Exception as e:
        logger.error(f"Error scheduling tasks: {str(e)}")

def update_weather_data():
    try:
        temperature, weather_description, precipitation = get_weather()
        if temperature is not None:
            logger.info(f"Weather updated: {temperature}C, {weather_description}, {precipitation}mm")
        else:
            logger.warning("Weather data returned None.")
    except Exception as e:
        logger.error(f"Error updating weather: {str(e)}")

def update_traffic_data():
    if not TELRAAM_API_CONFIG.get("enabled"):
        return
    try:
        headers = {'X-Api-Key': TELRAAM_API_CONFIG['api_key']}
        payload = {
            "time": "live",
            "level": "segments",
            "format": "per-hour",
            "id": TELRAAM_API_CONFIG['segment_id']
        }
        resp = requests.post(TELRAAM_API_CONFIG['api_url'], headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if 'features' in data and data['features']:
            traffic_counts = data['features'][0]['properties']['trafficData']
            influx_data = []
            for entry in traffic_counts:
                rec = {
                    "measurement": "telraam_traffic",
                    "tags": {"segment_id": TELRAAM_API_CONFIG['segment_id']},
                    "time": entry['date'],
                    "fields": {
                        "car": entry['car'],
                        "heavy": entry['heavy'],
                        "pedestrian": entry['pedestrian'],
                        "bike": entry['bike']
                    }
                }
                influx_data.append(rec)
            if INFLUXDB_CONFIG.get("enabled") and InfluxDB_CLIENT and write_api:
                try:
                    write_api.write(bucket=INFLUXDB_CONFIG['bucket'], record=influx_data)
                    logger.info("Telraam traffic data written to InfluxDB.")
                except Exception as e:
                    logger.error(f"Failed to write Telraam data: {str(e)}. Queueing.")
                    failed_writes_queue.put((INFLUXDB_CONFIG['bucket'], influx_data))
        else:
            logger.warning("No traffic data in Telraam response.")
    except Exception as e:
        logger.error(f"Error updating Telraam data: {str(e)}")

def retry_failed_writes():
    if not (INFLUXDB_CONFIG.get("enabled") and InfluxDB_CLIENT and write_api):
        logger.debug("InfluxDB disabled or not configured; skipping retries.")
        return
    while not failed_writes_queue.empty():
        bucket, data = failed_writes_queue.get()
        try:
            write_api.write(bucket=bucket, record=data)
            logger.info(f"Retried write to InfluxDB bucket '{bucket}' successfully.")
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB on retry: {str(e)}. Re-queueing.")
            failed_writes_queue.put((bucket, data))
            break

####################################
# STARTUP NOTIFICATIONS
####################################
def notify_on_start():
    hostname = socket.gethostname()
    local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # If serial is used or not
    if use_serial_device:
        status_serial = f"Using serial on {SERIAL_CONFIG.get('port','?')}"
    else:
        status_serial = "Serial not used"

    usb_dev_check = detect_usb_device(verbose=False)
    usb_status = "USB sound meter detected" if usb_dev_check else "USB not detected"

    influxdb_url = f"https://{INFLUXDB_CONFIG['host']}:{INFLUXDB_CONFIG['port']}" if INFLUXDB_CONFIG.get("enabled") else "N/A"
    mqtt_status = "Connected" if mqtt_connected else "Not connected"
    influxdb_status = "Connected" if InfluxDB_CLIENT else "Not connected"
    weather_status = "Enabled" if WEATHER_CONFIG.get("enabled") else "Disabled"

    message = (
        f"**Noise Buster Client Started**\n"
        f"Hostname: **{hostname}**\n"
        f"Status: **Client started successfully**\n"
        f"InfluxDB URL: **{influxdb_url}**\n"
        f"InfluxDB Connection: **{influxdb_status}**\n"
        f"MQTT Connection: **{mqtt_status}**\n"
        f"USB Sound Meter: **{usb_status}**\n"
        f"Serial Status: **{status_serial}**\n"
        f"Minimum Noise Level: **{DEVICE_AND_NOISE_MONITORING_CONFIG['minimum_noise_level']} dB**\n"
        f"Camera Usage: **{'IP Camera' if CAMERA_CONFIG.get('use_ip_camera') else 'None'}**\n"
        f"Telraam Usage: **{'Enabled' if TELRAAM_API_CONFIG.get('enabled') else 'Disabled'}**\n"
        f"Weather Data: **{weather_status}**\n"
        f"Timezone: **UTC{TIMEZONE_CONFIG.get('timezone_offset', 0):+}**\n"
        f"Local Time: **{local_time}**\n"
    )
    send_discord_notification(message)

####################################
# MAIN
####################################
def main():
    # Quick config checks
    dev_check = None
    if use_serial_device:
        s = detect_serial_device(verbose=False)
        if not s:
            logger.warning("Serial device not found - fallback to USB.")
            dev_check = detect_usb_device(verbose=False)
            if not dev_check:
                logger.error("No USB device found either. Exiting.")
                sys.exit(1)
            else:
                logger.info("We'll use USB fallback.")
        else:
            logger.info("Starting Noise Monitoring on Serial device.")
    else:
        dev_check = detect_usb_device(verbose=False)
        if not dev_check:
            logger.error("No USB sound meter found, serial disabled. Exiting.")
            sys.exit(1)
        logger.info("Starting Noise Monitoring on USB device.")

    # Possibly send a Pushover on start
    if PUSHOVER_CONFIG.get("enabled"):
        send_pushover_notification("Noise Buster has started monitoring.")

    notify_on_start()

    # Start noise monitoring in separate thread
    noise_thread = threading.Thread(target=update_noise_level)
    noise_thread.daemon = True
    noise_thread.start()

    # Schedule tasks
    schedule_tasks()

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Manual interruption by user.")

if __name__ == "__main__":
    main()
