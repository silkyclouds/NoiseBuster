#!/usr/bin/env python3
# NoiseBuster - created by Raphaël Vael
# License: CC BY-NC 4.0
#
# Changelog:
#   - [Initial Versions] Raphaël Vael: Base implementation & main dev
#   - [Commit by Mark Deneen] Improved MQTT support
#   - [Commit by Alexander Koch] Added serial device support
#
# This script monitors noise levels from either a USB sound meter or a serial-based device,
# then logs/publishes data to various services (InfluxDB, MQTT, Discord, etc.).

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

# Required modules (for USB-based sound meter and scheduling)
required_modules = [
    'usb.core',
    'usb.util',
    'requests',
    'schedule',
]

# Attempt to import required modules
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

# Now import the required modules
import usb.core
import usb.util
import requests
import schedule

# Try to import serial if we need it
try:
    import serial
except ImportError:
    serial = None

# Now load configuration
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

# Retrieve USB device IDs from the configuration
usb_vendor_id = DEVICE_AND_NOISE_MONITORING_CONFIG.get("usb_vendor_id", "")
usb_product_id = DEVICE_AND_NOISE_MONITORING_CONFIG.get("usb_product_id", "")

# Convert IDs from config to integers if specified
usb_vendor_id_int = int(usb_vendor_id, 16) if usb_vendor_id else None
usb_product_id_int = int(usb_product_id, 16) if usb_product_id else None

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

# File handler
fh = logging.FileHandler('noisebuster.log')
fh.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(file_formatter)

logger.addHandler(ch)
logger.addHandler(fh)
logger.info("Detailed logs are saved in 'noisebuster.log'.")

####################################
# LOAD USB IDs FILE
####################################
def load_usb_ids(usb_ids_path):
    usb_ids = []
    try:
        with open(usb_ids_path, 'r') as usb_ids_file:
            for line in usb_ids_file:
                line_content, sep, comment = line.partition('#')
                line_content = line_content.strip()
                if not line_content:
                    continue
                parts = line_content.strip().split(',')
                if len(parts) >= 2:
                    vendor_id_str, product_id_str = parts[0], parts[1]
                    model = comment.strip() if comment else "Unknown model"
                    vendor_id = int(vendor_id_str, 16)
                    product_id = int(product_id_str, 16)
                    usb_ids.append((vendor_id, product_id, model))
                else:
                    logger.warning(f"Incorrect format in USB IDs file: {line.strip()}")
    except FileNotFoundError:
        logger.warning(f"USB IDs file '{usb_ids_path}' not found. Automatic detection may fail for unknown devices.")
    return usb_ids

usb_ids = load_usb_ids('usb_ids')

####################################
# OPTIONAL MODULES
####################################
InfluxDBClient = None
SYNCHRONOUS = None
mqtt = None
cv2 = None
np = None

def import_optional_modules():
    global InfluxDBClient, SYNCHRONOUS, mqtt, cv2, np
    missing_optional_modules = []

    if INFLUXDB_CONFIG.get("enabled"):
        try:
            from influxdb_client import InfluxDBClient as InfluxDBClientImported
            from influxdb_client.client.write_api import SYNCHRONOUS as SYNCHRONOUS_IMPORTED
            InfluxDBClient = InfluxDBClientImported
            SYNCHRONOUS = SYNCHRONOUS_IMPORTED
        except ImportError:
            logger.error("InfluxDB client library not installed. Please install 'influxdb-client' package.")
            missing_optional_modules.append('influxdb_client')

    if MQTT_CONFIG.get("enabled"):
        try:
            import paho.mqtt.client as mqtt_imported
            mqtt = mqtt_imported
        except ImportError:
            logger.error("MQTT client library not installed. Please install 'paho-mqtt' package.")
            missing_optional_modules.append('paho-mqtt')

    if CAMERA_CONFIG.get("use_ip_camera"):
        try:
            import cv2 as cv2_imported
            import numpy as np_imported
            cv2 = cv2_imported
            np = np_imported
        except ImportError:
            logger.error("OpenCV or numpy library not installed. Please install 'opencv-python' + 'numpy'.")
            missing_optional_modules.append('opencv-python, numpy')

    return missing_optional_modules

missing_optional_modules = import_optional_modules()

####################################
# CONFIG VALIDATION
####################################
def check_configuration():
    logger.info("Checking configuration...")

    # InfluxDB
    if INFLUXDB_CONFIG.get("enabled"):
        influxdb_missing_fields = []
        required_fields = ["host", "port", "token", "org", "bucket", "realtime_bucket"]
        for field in required_fields:
            if not INFLUXDB_CONFIG.get(field) or (
                isinstance(INFLUXDB_CONFIG.get(field), str)
                and INFLUXDB_CONFIG.get(field).startswith("<YOUR_")
            ):
                influxdb_missing_fields.append(field)

        # Check mandatory bucket names
        bucket_name = INFLUXDB_CONFIG.get("bucket", "")
        realtime_bucket_name = INFLUXDB_CONFIG.get("realtime_bucket", "")
        if bucket_name != "noise_buster":
            logger.error("InfluxDB 'bucket' must be 'noise_buster'. Please fix in config.json.")
            influxdb_missing_fields.append('bucket')
        if realtime_bucket_name != "noise_buster_realtime":
            logger.error("InfluxDB 'realtime_bucket' must be 'noise_buster_realtime'. Please fix in config.json.")
            influxdb_missing_fields.append('realtime_bucket')

        if influxdb_missing_fields:
            logger.error(f"InfluxDB is enabled but missing: {', '.join(influxdb_missing_fields)}. Disabling.")
            INFLUXDB_CONFIG["enabled"] = False
        else:
            logger.info("InfluxDB is enabled and properly configured.")
    else:
        logger.info("InfluxDB is disabled.")

    # Pushover
    if PUSHOVER_CONFIG.get("enabled"):
        pushover_missing_fields = []
        required_fields = ["user_key", "api_token"]
        for field in required_fields:
            if not PUSHOVER_CONFIG.get(field) or PUSHOVER_CONFIG.get(field).startswith("<YOUR_"):
                pushover_missing_fields.append(field)
        if pushover_missing_fields:
            logger.error(f"Pushover missing config: {', '.join(pushover_missing_fields)}. Disabling.")
            PUSHOVER_CONFIG["enabled"] = False
        else:
            logger.info("Pushover is enabled and properly configured.")
    else:
        logger.info("Pushover is disabled.")

    # Weather
    if WEATHER_CONFIG.get("enabled"):
        weather_missing_fields = []
        required_fields = ["api_key", "api_url", "location"]
        for field in required_fields:
            if not WEATHER_CONFIG.get(field) or WEATHER_CONFIG.get(field).startswith("<YOUR_"):
                weather_missing_fields.append(field)
        if weather_missing_fields:
            logger.error(f"Weather missing config: {', '.join(weather_missing_fields)}. Disabling.")
            WEATHER_CONFIG["enabled"] = False
        else:
            logger.info("Weather data collection is enabled and properly configured.")
    else:
        logger.info("Weather data collection is disabled.")

    # MQTT
    if MQTT_CONFIG.get("enabled"):
        mqtt_missing_fields = []
        required_fields = ["server", "port"]
        for field in required_fields:
            if not MQTT_CONFIG.get(field):
                mqtt_missing_fields.append(field)
        if mqtt_missing_fields:
            logger.error(f"MQTT missing: {', '.join(mqtt_missing_fields)}. Disabling.")
            MQTT_CONFIG["enabled"] = False
        else:
            logger.info("MQTT is enabled and properly configured.")
    else:
        logger.info("MQTT is disabled.")

    # Camera
    if CAMERA_CONFIG.get("use_ip_camera"):
        camera_missing_fields = []
        required_fields = ["ip_camera_url", "ip_camera_protocol"]
        for field in required_fields:
            if not CAMERA_CONFIG.get(field):
                camera_missing_fields.append(field)
        if camera_missing_fields:
            logger.error(f"IP Camera missing config: {', '.join(camera_missing_fields)}. Disabling.")
            CAMERA_CONFIG["use_ip_camera"] = False
        else:
            logger.info("IP Camera is enabled and properly configured.")
    else:
        logger.info("IP Camera is disabled.")

    # Telraam
    if TELRAAM_API_CONFIG.get("enabled"):
        telraam_missing_fields = []
        required_fields = ["api_key", "segment_id"]
        for field in required_fields:
            if not TELRAAM_API_CONFIG.get(field) or TELRAAM_API_CONFIG.get(field).startswith("<YOUR_"):
                telraam_missing_fields.append(field)
        if telraam_missing_fields:
            logger.error(f"Telraam missing config: {', '.join(telraam_missing_fields)}. Disabling.")
            TELRAAM_API_CONFIG["enabled"] = False
        else:
            logger.info("Telraam data collection is enabled and properly configured.")
    else:
        logger.info("Telraam data collection is disabled.")

    # Discord
    if DISCORD_CONFIG.get("enabled"):
        discord_missing_fields = []
        required_fields = ["webhook_url"]
        for field in required_fields:
            if not DISCORD_CONFIG.get(field) or DISCORD_CONFIG.get(field).startswith("<YOUR_"):
                discord_missing_fields.append(field)
        if discord_missing_fields:
            logger.error(f"Discord missing config: {', '.join(discord_missing_fields)}. Disabling.")
            DISCORD_CONFIG["enabled"] = False
        else:
            logger.info("Discord notifications are enabled and properly configured.")
    else:
        logger.info("Discord notifications are disabled.")

    # Device & Noise
    if not DEVICE_AND_NOISE_MONITORING_CONFIG.get("minimum_noise_level"):
        logger.error("Minimum noise level not set in DEVICE_AND_NOISE_MONITORING_CONFIG.")
    else:
        logger.info(f"Minimum noise level set to {DEVICE_AND_NOISE_MONITORING_CONFIG.get('minimum_noise_level')} dB.")

    if (not DEVICE_AND_NOISE_MONITORING_CONFIG.get("usb_vendor_id")
       or not DEVICE_AND_NOISE_MONITORING_CONFIG.get("usb_product_id")):
        logger.warning("USB Vendor/Product ID not set or incomplete. Will try autodetection if use_usb_device is chosen.")

check_configuration()

####################################
# GLOBAL STATE
####################################
device_detected = False

####################################
# USB DEVICE DETECTION
####################################
def detect_usb_device(verbose=True):
    global device_detected
    devices = usb.core.find(find_all=True)

    for dev in devices:
        dev_vendor_id = dev.idVendor
        dev_product_id = dev.idProduct

        # If config specifically sets usb_vendor_id/usb_product_id
        if usb_vendor_id_int and usb_product_id_int:
            if dev_vendor_id == usb_vendor_id_int and dev_product_id == usb_product_id_int:
                if verbose or not device_detected:
                    model = next((name for vid, pid, name in usb_ids
                                  if vid == dev_vendor_id and pid == dev_product_id), None)
                    if model:
                        logger.info(f"Detected specified device: {model} (Vendor {hex(dev_vendor_id)}, Product {hex(dev_product_id)})")
                    else:
                        logger.info("User-defined USB sound meter detected. Please share device info to add to official list.")
                device_detected = True
                return dev
        # Otherwise, check known usb_ids file
        elif any((dev_vendor_id, dev_product_id) == (vid, pid) for vid, pid, _ in usb_ids):
            if verbose or not device_detected:
                model = next((name for vid, pid, name in usb_ids
                              if vid == dev_vendor_id and pid == dev_product_id),
                             "Unknown model")
                logger.info(f"{model} sound meter detected: Vendor {hex(dev_vendor_id)}, Product {hex(dev_product_id)}")
            device_detected = True
            return dev
        else:
            # No match, keep searching
            if verbose and not device_detected:
                logger.info(f"Ignoring non-sound device: Vendor {hex(dev_vendor_id)}, Product {hex(dev_product_id)}")

    # No device found
    if usb_vendor_id_int and usb_product_id_int:
        if verbose or device_detected:
            logger.error("Specified USB device not found. Check cable/IDs in config.json.")
    else:
        if verbose or device_detected:
            logger.error("No known USB device found. Autodetection failed or device not connected.")
    device_detected = False
    return None

####################################
# SERIAL DETECTION
####################################
def detect_serial_device(verbose=True):
    """Attempt to open a serial device as configured in SERIAL_CONFIG."""
    if not serial:
        logger.error("PySerial is not installed. Please install 'pyserial'.")
        return None
    if not SERIAL_CONFIG.get("enabled"):
        logger.info("Serial device is not enabled in config. Skipping serial detection.")
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
# INFLUXDB CONNECTION
####################################
failed_writes_queue = Queue()

InfluxDB_CLIENT = None
write_api = None

def connect_influxdb():
    if INFLUXDB_CONFIG.get("enabled") and InfluxDBClient:
        try:
            protocol = "https" if INFLUXDB_CONFIG.get("ssl") else "http"
            client = InfluxDBClient(
                url=f"{protocol}://{INFLUXDB_CONFIG['host']}:{INFLUXDB_CONFIG['port']}",
                token=INFLUXDB_CONFIG['token'],
                org=INFLUXDB_CONFIG['org'],
                timeout=INFLUXDB_CONFIG.get('timeout', 20000)
            )
            w_api = client.write_api(write_options=SYNCHRONOUS)
            return client, w_api
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            INFLUXDB_CONFIG["enabled"] = False
            return None, None
    else:
        return None, None

InfluxDB_CLIENT, write_api = connect_influxdb()

####################################
# MQTT INITIALIZATION
####################################
mqtt_client = None
mqtt_connected = False

if MQTT_CONFIG.get("enabled") and mqtt:
    mqtt_client = mqtt.Client()  # might cause DeprecationWarning for v1 callbacks
    if MQTT_CONFIG.get("user") and MQTT_CONFIG.get("password"):
        mqtt_client.username_pw_set(MQTT_CONFIG["user"], MQTT_CONFIG["password"])
    try:
        availability_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/noise_level/availability"
        mqtt_client.will_set(availability_topic, payload="offline", qos=1, retain=True)
        mqtt_client.connect(MQTT_CONFIG["server"], MQTT_CONFIG["port"], 60)
        mqtt_client.loop_start()
        mqtt_connected = True
        logger.info("MQTT client connected successfully.")

        # Publish sensor config for Home Assistant
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
            logger.info(f"Sensor configuration published to {config_topic}")
            mqtt_client.publish(availability_topic, "online", qos=1, retain=True)
            logger.info(f"Sensor availability published to {availability_topic}")

        if mqtt_connected:
            publish_sensor_config()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {str(e)}")
        MQTT_CONFIG["enabled"] = False
else:
    if MQTT_CONFIG.get("enabled") and not mqtt:
        logger.error("MQTT is enabled but paho-mqtt is not installed. Disabling.")
        MQTT_CONFIG["enabled"] = False

####################################
# DISCORD NOTIFICATION
####################################
def send_discord_notification(message):
    if DISCORD_CONFIG.get("enabled"):
        webhook_url = DISCORD_CONFIG.get("webhook_url")
        if webhook_url and not webhook_url.startswith("<YOUR_"):
            try:
                data = {"content": message}
                response = requests.post(webhook_url, json=data)
                if response.status_code == 204:
                    logger.info("Discord notification sent successfully.")
                else:
                    logger.error(f"Failed to send Discord notification: {response.status_code}, {response.text}")
            except Exception as e:
                logger.error(f"Error sending Discord notification: {str(e)}")
                logger.debug("Exception details:", exc_info=True)
        else:
            logger.error("Discord webhook URL missing or invalid. Disabling feature.")
            DISCORD_CONFIG["enabled"] = False

####################################
# PUSHOVER NOTIFICATION
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
                logger.debug("Exception details:", exc_info=True)
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
# IMAGE CAPTURE
####################################
def capture_image(current_peak_dB, peak_temperature, peak_weather_description, peak_precipitation, timestamp):
    if CAMERA_CONFIG.get("use_ip_camera"):
        if cv2 is None:
            logger.error("OpenCV not installed. Please install 'opencv-python'.")
            return
        cap = cv2.VideoCapture(CAMERA_CONFIG["ip_camera_url"])
        ret, frame = cap.read()
        cap.release()
    else:
        logger.info("No camera configured or camera usage is disabled.")
        return

    if frame is not None:
        formatted_time = timestamp.strftime("%Y-%m-%d_%H:%M:%S")
        weather_info = f"{peak_weather_description.replace(' ', '_')}_{peak_temperature}C"
        filename = f"{formatted_time}_{weather_info}.jpg"
        filepath = os.path.join(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path'], filename)

        if not os.path.exists(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path']):
            os.makedirs(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path'])
            logger.info(f"Image directory created: {DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path']}")

        text_lines = [
            f"Time: {formatted_time}",
            f"Noise: {current_peak_dB} dB",
            f"Temp: {peak_temperature} C",
            f"Weather: {peak_weather_description}",
            f"Precipitation: {peak_precipitation} mm"
        ]
        y_position = 50
        for line in text_lines:
            cv2.putText(frame, line, (10, y_position),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_position += 30
        cv2.imwrite(filepath, frame)
        logger.info(f"Image saved: {filepath}")

def delete_old_images():
    image_path = DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path']
    if not os.path.exists(image_path):
        os.makedirs(image_path)
        logger.info(f"Image directory created: {image_path}")

    current_time = datetime.now()
    for filename in os.listdir(image_path):
        filepath = os.path.join(image_path, filename)
        if os.path.isfile(filepath):
            file_creation_time = datetime.fromtimestamp(os.path.getctime(filepath))
            time_difference = current_time - file_creation_time
            if time_difference > timedelta(hours=DEVICE_AND_NOISE_MONITORING_CONFIG['image_retention_hours']):
                os.remove(filepath)
                logger.info(f"Deleted old image: {filepath}")

####################################
# WEATHER FETCH
####################################
def get_weather():
    if not WEATHER_CONFIG.get("enabled"):
        return None, None, 0.0
    try:
        response = requests.get(
            f"{WEATHER_CONFIG['api_url']}?q={WEATHER_CONFIG['location']}&appid={WEATHER_CONFIG['api_key']}&units=metric"
        )
        response.raise_for_status()
        weather_data = response.json()
        temperature = float(weather_data['main']['temp'])
        weather_description = weather_data['weather'][0]['description']
        precipitation_float = 0.0

        if 'rain' in weather_data and '1h' in weather_data['rain']:
            precipitation_float += float(weather_data['rain']['1h'])
        if 'snow' in weather_data and '1h' in weather_data['snow']:
            precipitation_float += float(weather_data['snow']['1h'])

        return temperature, weather_description, precipitation_float
    except requests.RequestException as e:
        logger.error(f"Failed to get weather data: {str(e)}")
        logger.debug("Exception details:", exc_info=True)
        return None, None, 0.0

####################################
# MAIN NOISE MONITORING
####################################
def update_noise_level():
    """Monitor noise levels from either USB or serial, record events, publish data."""
    window_start_time = time.time()
    current_peak_dB = 0
    peak_temperature = None
    peak_weather_description = ""
    peak_precipitation_float = 0.0

    usb_dev = None
    ser_dev = None

    # Decide which device to open
    if use_serial_device:
        ser_dev = detect_serial_device(verbose=True)
        if not ser_dev:
            logger.error("No serial device found. Exiting.")
            sys.exit(1)
        logger.info("Sound meter (serial) connected.")
    else:
        usb_dev = detect_usb_device(verbose=True)
        if not usb_dev:
            logger.error("No USB device found. Exiting.")
            sys.exit(1)
        logger.info("Sound meter (USB) connected.")

    while True:
        current_time = time.time()
        if current_time - window_start_time >= DEVICE_AND_NOISE_MONITORING_CONFIG['time_window_duration']:
            timestamp = datetime.utcnow()
            delete_old_images()
            logger.info(f"Time window elapsed. Current peak dB: {round(current_peak_dB, 1)}")

            # Prepare data
            realtime_data = [{
                "measurement": "noise_buster_events",
                "tags": {"location": "noise_buster"},
                "time": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": {"noise_level": round(current_peak_dB, 1)}
            }]

            logger.info(f"Current noise level: {round(current_peak_dB, 1)} dB")

            # InfluxDB real-time
            if INFLUXDB_CONFIG.get("enabled") and InfluxDB_CLIENT and write_api:
                try:
                    write_api.write(bucket=INFLUXDB_CONFIG['realtime_bucket'], record=realtime_data)
                    logger.info(f"All noise levels written to realtime bucket: {round(current_peak_dB, 1)} dB")
                except Exception as e:
                    logger.error(f"Failed to write to InfluxDB: {str(e)}. Queueing.")
                    logger.debug("Exception details:", exc_info=True)
                    failed_writes_queue.put((INFLUXDB_CONFIG['realtime_bucket'], [realtime_data]))
            else:
                logger.debug("InfluxDB is disabled or not configured for real-time bucket.")

            # MQTT real-time
            if mqtt_client and MQTT_CONFIG.get("enabled"):
                realtime_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/realtime_noise_levels/state"
                realtime_payload = json.dumps(realtime_data[0]['fields'])
                send_to_mqtt(realtime_topic, realtime_payload)

            # If above threshold
            if current_peak_dB >= DEVICE_AND_NOISE_MONITORING_CONFIG['minimum_noise_level']:
                peak_temp_float = float(peak_temperature) if peak_temperature is not None else 0.0
                peak_weather_descr = peak_weather_description if peak_weather_description else ""
                main_data = {
                    "measurement": "noise_buster_events",
                    "tags": {"location": "noise_buster"},
                    "time": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "fields": {
                        "noise_level": round(current_peak_dB, 1),
                        "temperature": peak_temp_float,
                        "weather_description": peak_weather_descr,
                        "precipitation": peak_precipitation_float
                    }
                }

                logger.info(f"Noise level exceeded threshold: {round(current_peak_dB, 1)} dB")

                # InfluxDB main
                if INFLUXDB_CONFIG.get("enabled") and InfluxDB_CLIENT and write_api:
                    try:
                        write_api.write(bucket=INFLUXDB_CONFIG['bucket'], record=main_data)
                        logger.info(f"High noise level data written to main bucket: {main_data}")
                    except Exception as e:
                        logger.error(f"Failed to write to InfluxDB: {str(e)}. Queueing.")
                        logger.debug("Exception details:", exc_info=True)
                        failed_writes_queue.put((INFLUXDB_CONFIG['bucket'], [main_data]))
                else:
                    logger.debug("InfluxDB disabled or not configured for main bucket.")

                # MQTT event
                if mqtt_client and MQTT_CONFIG.get("enabled"):
                    event_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/noise_levels/state"
                    event_payload = json.dumps(main_data['fields'])
                    send_to_mqtt(event_topic, event_payload)

                capture_image(current_peak_dB, peak_temp_float, peak_weather_descr, peak_precipitation_float, timestamp)

            # Reset window
            window_start_time = current_time
            current_peak_dB = 0
            peak_temperature = None
            peak_weather_description = ""
            peak_precipitation_float = 0.0

        # Read from device
        try:
            if usb_dev:
                ret = usb_dev.ctrl_transfer(0xC0, 4, 0, 0, 200)
                dB = (ret[0] + ((ret[1] & 3) * 256)) * 0.1 + 30
                dB = round(dB, 1)
                if dB > current_peak_dB:
                    current_peak_dB = dB
                    if WEATHER_CONFIG.get("enabled"):
                        peak_temperature, peak_weather_description, precipitation = get_weather()
                        peak_precipitation_float = float(precipitation)
            elif ser_dev:
                line = ser_dev.readline().decode().strip()
                if line:
                    dB = float(line)
                    if dB > current_peak_dB:
                        current_peak_dB = dB
                        if WEATHER_CONFIG.get("enabled"):
                            peak_temperature, peak_weather_description, precipitation = get_weather()
                            peak_precipitation_float = float(precipitation)
            else:
                logger.error("No device found (neither USB nor Serial). Breaking loop.")
                break

        except usb.core.USBError as usb_err:
            logger.error(f"USB Error reading from device: {str(usb_err)}")
            logger.debug("Exception details:", exc_info=True)
            usb_dev = detect_usb_device(verbose=False)
            if not usb_dev:
                logger.error("Device not found on re-scan.")
            else:
                logger.info("Reconnected to USB device.")
        except Exception as e:
            logger.error(f"Unexpected error reading from device: {str(e)}")
            logger.debug("Exception details:", exc_info=True)

        time.sleep(0.1)

####################################
# SCHEDULING
####################################
def schedule_tasks():
    try:
        if TELRAAM_API_CONFIG.get("enabled"):
            interval = TELRAAM_API_CONFIG["request_interval_minutes"]
            schedule.every(interval).minutes.do(update_traffic_data)
            logger.info(f"Telraam tasks scheduled every {interval} minutes.")

        if WEATHER_CONFIG.get("enabled"):
            schedule.every(5).minutes.do(update_weather_data)
            logger.info("Weather data task scheduled every 5 minutes.")

        if INFLUXDB_CONFIG.get("enabled"):
            schedule.every(1).minutes.do(retry_failed_writes)
    except Exception as e:
        logger.error("Error scheduling tasks: " + str(e))
        logger.debug("Exception details:", exc_info=True)

def update_weather_data():
    try:
        temperature, weather_description, precipitation = get_weather()
        if temperature is not None:
            logger.info(f"Weather updated: {temperature}C, {weather_description}, {precipitation}mm")
        else:
            logger.warning("Weather data update returned None.")
    except Exception as e:
        logger.error(f"Error updating weather: {str(e)}")
        logger.debug("Exception details:", exc_info=True)

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
        response = requests.post(TELRAAM_API_CONFIG['api_url'], headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if 'features' in data and data['features']:
            traffic_counts = data['features'][0]['properties']['trafficData']
            influx_data = []
            for entry in traffic_counts:
                record = {
                    "measurement": "telraam_traffic",
                    "tags": {"segment_id": TELRAAM_API_CONFIG['segment_id']},
                    "time": entry['date'],  # Use the date from entry
                    "fields": {
                        "car": entry['car'],
                        "heavy": entry['heavy'],
                        "pedestrian": entry['pedestrian'],
                        "bike": entry['bike']
                    }
                }
                influx_data.append(record)

            if INFLUXDB_CONFIG.get("enabled") and InfluxDB_CLIENT and write_api:
                try:
                    write_api.write(bucket=INFLUXDB_CONFIG['bucket'], record=influx_data)
                    logger.info("Telraam traffic data written to InfluxDB.")
                except Exception as e:
                    logger.error(f"Failed to write Telraam data to InfluxDB: {str(e)}. Queueing.")
                    logger.debug("Exception details:", exc_info=True)
                    failed_writes_queue.put((INFLUXDB_CONFIG['bucket'], influx_data))
            else:
                logger.debug("InfluxDB disabled or not configured for Telraam data.")
        else:
            logger.warning("No traffic data in Telraam response.")
    except Exception as e:
        logger.error(f"Error updating Telraam data: {str(e)}")
        logger.debug("Exception details:", exc_info=True)

def retry_failed_writes():
    if not (INFLUXDB_CONFIG.get("enabled") and InfluxDB_CLIENT and write_api):
        logger.debug("InfluxDB disabled or not configured; skipping failed writes retry.")
        return

    while not failed_writes_queue.empty():
        bucket, data = failed_writes_queue.get()
        try:
            write_api.write(bucket=bucket, record=data)
            logger.info(f"Retried successfully writing data to InfluxDB bucket '{bucket}'.")
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB on retry: {str(e)}. Re-queueing.")
            logger.debug("Exception details:", exc_info=True)
            failed_writes_queue.put((bucket, data))
            break

####################################
# STARTUP NOTIFICATIONS
####################################
def notify_on_start():
    hostname = socket.gethostname()
    local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Quick info
    if not use_serial_device:
        try:
            dev_check = detect_usb_device(verbose=False)
            usb_status = "USB sound meter detected" if dev_check else "USB not detected"
        except Exception as e:
            usb_status = f"Error detecting USB: {str(e)}"
    else:
        usb_status = "Using serial device, no USB used"

    serial_status = "Serial not used"
    if use_serial_device:
        serial_status = f"Using serial device on {SERIAL_CONFIG.get('port','?')}"

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
        f"Serial Status: **{serial_status}**\n"
        f"Minimum Noise Level: **{DEVICE_AND_NOISE_MONITORING_CONFIG['minimum_noise_level']} dB**\n"
        f"Camera Usage: **{'IP Camera' if CAMERA_CONFIG.get('use_ip_camera') else 'None'}**\n"
        f"Telraam Usage: **{'Enabled' if TELRAAM_API_CONFIG.get('enabled') else 'Disabled'}**\n"
        f"Weather Data Collection: **{weather_status}**\n"
        f"Timezone: **UTC{TIMEZONE_CONFIG.get('timezone_offset', 0):+}**\n"
        f"Local Time: **{local_time}**\n"
    )
    send_discord_notification(message)

####################################
# MAIN
####################################
def main():
    # Quick device check
    if use_serial_device:
        test_serial = detect_serial_device(verbose=False)
        if not test_serial:
            logger.error("Serial device not found. Check config or cable.")
            sys.exit(1)
        logger.info("Starting Noise Monitoring on serial device.")
    else:
        test_usb = detect_usb_device(verbose=False)
        if not test_usb:
            logger.error("USB sound meter not found. Check config or cable.")
            sys.exit(1)
        logger.info("Starting Noise Monitoring on USB device.")

    # Notify startup
    if PUSHOVER_CONFIG.get("enabled"):
        send_pushover_notification("Noise Buster has started monitoring.")
    notify_on_start()

    # Start noise monitoring in a thread
    noise_monitoring_thread = threading.Thread(target=update_noise_level)
    noise_monitoring_thread.daemon = True
    noise_monitoring_thread.start()

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
