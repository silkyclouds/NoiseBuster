import os
import logging
import json
import usb.core
import usb.util
import time
import traceback
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
import http.client
import urllib.parse
import requests
import paho.mqtt.client as mqtt
import picamera
import cv2
import numpy as np
from io import BytesIO
import base64
import schedule
import threading
from queue import Queue
import socket

# Configure logging level and output format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration from JSON file
def load_config(config_path):
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    return config

config = load_config('config.json')

# Configuration
INFLUXDB_CONFIG = config["INFLUXDB_CONFIG"]
PUSHOVER_CONFIG = config["PUSHOVER_CONFIG"]
WEATHER_CONFIG = config["WEATHER_CONFIG"]
MQTT_CONFIG = config["MQTT_CONFIG"]
CAMERA_CONFIG = config["CAMERA_CONFIG"]
IMAGE_STORAGE_CONFIG = config["IMAGE_STORAGE_CONFIG"]
DEVICE_AND_NOISE_MONITORING_CONFIG = config["DEVICE_AND_NOISE_MONITORING_CONFIG"]
TELRAAM_API_CONFIG = config["TELRAAM_API_CONFIG"]
TIMEZONE_CONFIG = config["TIMEZONE_CONFIG"]
DISCORD_CONFIG = config["DISCORD_CONFIG"]

failed_writes_queue = Queue()

# Connect to InfluxDB if enabled
if INFLUXDB_CONFIG["enabled"]:
    def connect_influxdb():
        protocol = "https" if INFLUXDB_CONFIG["ssl"] else "http"
        influxdb_client = InfluxDBClient(
            url=f"{protocol}://{INFLUXDB_CONFIG['host']}:{INFLUXDB_CONFIG['port']}",
            token=INFLUXDB_CONFIG['token'],
            org=INFLUXDB_CONFIG['org'],
            timeout=INFLUXDB_CONFIG['timeout']
        )
        write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
        return influxdb_client, write_api

    influxdb_client, write_api = connect_influxdb()
else:
    influxdb_client, write_api = None, None

# Connect to MQTT if enabled
mqtt_connected = False
if MQTT_CONFIG["enabled"]:
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(MQTT_CONFIG["user"], MQTT_CONFIG["password"])
    try:
        mqtt_client.connect(MQTT_CONFIG["server"], MQTT_CONFIG["port"], 60)
        mqtt_client.loop_start()
        mqtt_connected = True
        logger.info("MQTT client connected successfully.")

        # Publish sensor configuration
        def publish_sensor_config():
            """Publish sensor configuration to MQTT for Home Assistant integration."""
            noise_sensor_config = {
                "device_class": "sound",
                "name": f"{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']} Noise Level",
                "state_topic": f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/noise_levels/state",
                "unit_of_measurement": "dB",
                "value_template": "{{ value_json.noise_level }}",
                "unique_id": f"{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}_noise_level_sensor",
                "availability_topic": f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/availability",
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

        if mqtt_connected:
            publish_sensor_config()
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {str(e)}")

# Send Discord notification if enabled
def send_discord_notification(message):
    if DISCORD_CONFIG["enabled"]:
        data = {"content": message}
        response = requests.post(DISCORD_CONFIG["webhook_url"], json=data)
        if response.status_code == 204:
            logger.info("Discord notification sent successfully.")
        else:
            logger.error(f"Failed to send Discord notification: {response.status_code}, {response.text}")

# Notify on start
def notify_on_start():
    hostname = socket.gethostname()
    local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        dev = detect_usb_device()
        usb_status = "USB sound meter detected" if dev else "USB sound meter not detected"
    except Exception as e:
        usb_status = f"Error detecting USB sound meter: {str(e)}"

    influxdb_url = f"https://{INFLUXDB_CONFIG['host']}:{INFLUXDB_CONFIG['port']}" if INFLUXDB_CONFIG["enabled"] else "N/A"
    mqtt_status = "Connected" if mqtt_connected else "Not connected"
    influxdb_status = "Connected" if INFLUXDB_CONFIG["enabled"] and influxdb_client.ping() else "Not connected"
    weather_status = "Enabled" if WEATHER_CONFIG["enabled"] else "Disabled"

    message = (
        f"**Noise Buster Client Started**\n"
        f"Hostname: **{hostname}**\n"
        f"Status: **Client started successfully**\n"
        f"InfluxDB URL: **{influxdb_url}**\n"
        f"InfluxDB Connection: **{influxdb_status}**\n"
        f"MQTT Connection: **{mqtt_status}**\n"
        f"USB Sound Meter: **{usb_status}**\n"
        f"Minimum Noise Level: **{DEVICE_AND_NOISE_MONITORING_CONFIG['minimum_noise_level']} dB**\n"
        f"Camera Usage: **{'IP Camera' if CAMERA_CONFIG['use_ip_camera'] else 'Pi Camera' if CAMERA_CONFIG['use_pi_camera'] else 'None'}**\n"
        f"Telraam Usage: **{'Enabled' if TELRAAM_API_CONFIG['enabled'] else 'Disabled'}**\n"
        f"Weather Data Collection: **{weather_status}**\n"
        f"Timezone: **UTC{TIMEZONE_CONFIG['timezone_offset']:+}**\n"
        f"Local Time: **{local_time}**\n"
    )
    send_discord_notification(message)

# Send Pushover notification if enabled
def send_pushover_notification(message):
    """Send notification via Pushover."""
    if PUSHOVER_CONFIG["enabled"]:
        conn = http.client.HTTPSConnection("api.pushover.net:443")
        conn.request("POST", "/1/messages.json",
                     urllib.parse.urlencode({
                         "token": PUSHOVER_CONFIG["api_token"],
                         "user": PUSHOVER_CONFIG["user_key"],
                         "message": message,
                         "title": PUSHOVER_CONFIG["title"]
                     }), {"Content-type": "application/x-www-form-urlencoded"})
        conn.getresponse()
        logger.info(f"Pushover notification sent: {message}")

# Send data to MQTT if enabled
def send_to_mqtt(topic, payload):
    """Publish data to MQTT topic."""
    if MQTT_CONFIG["enabled"]:
        mqtt_client.publish(topic, payload)
        logger.info(f"Data published to MQTT: {topic} -> {payload}")

# Detect USB sound meter device
def detect_usb_device():
    """Detect the USB sound meter automatically."""
    logger.info("Detecting USB sound meter...")
    devices = usb.core.find(find_all=True)
    specified_vendor_id = DEVICE_AND_NOISE_MONITORING_CONFIG.get('usb_vendor_id', "")
    specified_product_id = DEVICE_AND_NOISE_MONITORING_CONFIG.get('usb_product_id', "")
    for dev in devices:
        try:
            dev_desc = usb.util.get_string(dev, 256, dev.iProduct)
            dev_vendor_id = hex(dev.idVendor)
            dev_product_id = hex(dev.idProduct)
            logger.info(f"Detected device: {dev_desc} (Vendor ID: {dev_vendor_id}, Product ID: {dev_product_id})")

            if specified_vendor_id == "" or specified_product_id == "":
                if dev_desc and "sound" in dev_desc.lower():
                    logger.info(f"Assuming USB sound meter: {dev_desc}")
                    return dev
            else:
                if dev_vendor_id == specified_vendor_id and dev_product_id == specified_product_id:
                    logger.info(f"Found USB sound meter: {dev_desc} with Vendor ID: {dev_vendor_id} and Product ID: {dev_product_id}")
                    return dev
        except usb.core.USBError as e:
            logger.error(f"Failed to get USB device string: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during USB detection: {str(e)}")

    logger.warning("Specified USB device not found, listing all devices to detect sound meter.")
    return None

# Capture image using camera
def capture_image(current_peak_dB, peak_temperature, peak_weather_description, peak_precipitation, timestamp):
    if CAMERA_CONFIG["use_ip_camera"]:
        cap = cv2.VideoCapture(CAMERA_CONFIG["ip_camera_url"])
        ret, frame = cap.read()
        cap.release()
    elif CAMERA_CONFIG["use_pi_camera"]:
        with picamera.PiCamera() as camera:
            camera.resolution = CAMERA_CONFIG["resolution"]
            stream = BytesIO()
            camera.capture(stream, format='jpeg')
            stream.seek(0)
            frame = cv2.imdecode(np.frombuffer(stream.getvalue(), dtype=np.uint8), 1)
    else:
        logger.info("No camera configured or available for capturing images.")
        return

    if frame is not None:
        formatted_time = timestamp.strftime("%Y-%m-%d_%H:%M:%S")
        weather_info = f"{peak_weather_description.replace(' ', '_')}_{peak_temperature}C"
        filename = f"{formatted_time}_{weather_info}.jpg"
        filepath = os.path.join(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path'], filename)

        # Ensure the image save path exists
        if not os.path.exists(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path']):
            os.makedirs(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path'])

        text_lines = [
            f"Time: {formatted_time}",
            f"Noise: {current_peak_dB} dB",
            f"Temp: {peak_temperature} C",
            f"Weather: {peak_weather_description}",
            f"Precipitation: {peak_precipitation} mm"
        ]
        y_position = 50
        for line in text_lines:
            cv2.putText(frame, line, (10, y_position), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y_position += 30
        cv2.imwrite(filepath, frame)
        logger.info(f"Image saved: {filepath}")
        # Optionally, you can encode and store the image in the database if required

def delete_old_images():
    """Delete images older than retention period from the local storage."""
    current_time = datetime.now()
    for filename in os.listdir(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path']):
        filepath = os.path.join(DEVICE_AND_NOISE_MONITORING_CONFIG['image_save_path'], filename)
        if os.path.isfile(filepath):
            file_creation_time = datetime.fromtimestamp(os.path.getctime(filepath))
            time_difference = current_time - file_creation_time
            if time_difference > timedelta(hours=DEVICE_AND_NOISE_MONITORING_CONFIG['image_retention_hours']):
                os.remove(filepath)
                logger.info(f"Deleted old image: {filepath}")

# Fetch current weather data
def get_weather():
    """Fetch current weather data from OpenWeatherMap API including precipitation."""
    if not WEATHER_CONFIG["enabled"]:
        return None, None, 0.0

    try:
        response = requests.get(f"{WEATHER_CONFIG['api_url']}?q={WEATHER_CONFIG['location']}&appid={WEATHER_CONFIG['api_key']}&units=metric")
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
        return None, None, 0.0

# Global variable to track API failure state
api_failure_notified = False

def notify_api_failure():
    """Send notification in case of API error."""
    global api_failure_notified
    if not api_failure_notified:
        send_discord_notification("⚠️ Telraam API Error: Unable to connect to the Telraam API.")
        logger.info("API failure notification sent.")
        api_failure_notified = True

def notify_api_recovery():
    """Reset notification once the API is functional again."""
    global api_failure_notified
    if api_failure_notified:
        send_discord_notification("✅ Telraam API: Connection successfully restored.")
        logger.info("API recovery notification sent.")
        api_failure_notified = False

def fetch_traffic_data_with_retries(segment_id, time_start, time_end, api_key, data_format="per-hour", retries=3, delay=300):
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "level": "segments",
        "format": data_format,
        "id": segment_id,
        "time_start": time_start,
        "time_end": time_end
    }

    for attempt in range(retries):
        logger.info(f"Attempt {attempt+1} of {retries}: Fetching {data_format} traffic data for segment {segment_id}")
        try:
            response = requests.post(TELRAAM_API_CONFIG["api_url"], json=payload, headers=headers)
            response.raise_for_status()

            response_data = response.json()
            logger.info(f"API response: {response_data}")

            if "errorMessage" in response_data:
                logger.error(f"Telraam API Error: {response_data['errorMessage']}")
                notify_api_failure()  # Send failure notification
                return []

            # API is functional, reset the error flag
            notify_api_recovery()

            if 'report' in response_data:
                return response_data['report']
            else:
                logger.error("The 'report' key is missing from the API response")
                notify_api_failure()  # Send failure notification
                return []

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {data_format} traffic data: {str(e)}")
            notify_api_failure()  # Send failure notification
            if attempt < retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)  # Wait before retrying
            else:
                logger.error("All retry attempts failed.")
                return []

def aggregate_hourly_to_daily(hourly_data):
    daily_totals = {
        "heavy": 0,
        "car": 0,
        "bike": 0,
        "pedestrian": 0,
        "date": None,
        "segment_id": None
    }
    for record in hourly_data:
        daily_totals["heavy"] += record["heavy"]
        daily_totals["car"] += record["car"]
        daily_totals["bike"] += record["bike"]
        daily_totals["pedestrian"] += record["pedestrian"]
        if not daily_totals["date"]:
            daily_totals["date"] = record["date"][:10]  # Extract date part only
        if not daily_totals["segment_id"]:
            daily_totals["segment_id"] = record["segment_id"]
    return daily_totals

def store_traffic_data_in_influxdb(data, write_api):
    if not data:
        logger.warning("No traffic data to store.")
        return

    for record in data:
        fields = {
            "heavy": float(record["heavy"]),
            "car": float(record["car"]),
            "bike": float(record["bike"]),
            "pedestrian": float(record["pedestrian"])
        }

        # Include car_speed_hist_0to120plus as a string field if present
        if 'car_speed_hist_0to120plus' in record:
            fields["car_speed_hist_0to120plus"] = str(record["car_speed_hist_0to120plus"])

            # Break down car_speed_hist_0to120plus into individual fields
            car_speed_hist_120 = record["car_speed_hist_0to120plus"]
            speed_ranges_120 = [
                "0_5", "5_10", "10_15", "15_20", "20_25", "25_30", "30_35", "35_40",
                "40_45", "45_50", "50_55", "55_60", "60_65", "65_70", "70_75",
                "75_80", "80_85", "85_90", "90_95", "95_100", "100_105",
                "105_110", "110_115", "115_120", "120_plus"
            ]

            for i, speed_range in enumerate(speed_ranges_120):
                fields[f"car_speed_120_{speed_range}"] = car_speed_hist_120[i]

        # Include car_speed_hist_0to70plus as a string field if present
        if 'car_speed_hist_0to70plus' in record:
            fields["car_speed_hist_0to70plus"] = str(record["car_speed_hist_0to70plus"])

            # Break down car_speed_hist_0to70plus into individual fields
            car_speed_hist_70 = record["car_speed_hist_0to70plus"]
            speed_ranges_70 = [
                "0_10", "10_20", "20_30", "30_40", "40_50", "50_60", "60_70", "70_plus"
            ]

            for i, speed_range in enumerate(speed_ranges_70):
                fields[f"car_speed_70_{speed_range}"] = car_speed_hist_70[i]

        point = {
            "measurement": "traffic_data",
            "time": record["date"],
            "tags": {
                "segment_id": str(record["segment_id"])
            },
            "fields": fields
        }

        try:
            write_api.write(bucket=INFLUXDB_CONFIG['bucket'], record=[point])
            logger.info(f"Stored traffic data for {record['date']} in InfluxDB.")

            # Publish to MQTT
            state_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/traffic_data/state"
            payload = json.dumps(fields)
            send_to_mqtt(state_topic, payload)

        except Exception as e:
            logger.error(f"Failed to write traffic data to InfluxDB: {str(e)}. Adding to queue.")
            failed_writes_queue.put((INFLUXDB_CONFIG['bucket'], [point]))

def retry_failed_writes():
    """Retry writing failed writes to InfluxDB."""
    global influxdb_client, write_api
    if not failed_writes_queue.empty():
        logger.info("Retrying failed writes to InfluxDB.")
    try:
        while not failed_writes_queue.empty():
            bucket, points = failed_writes_queue.get()
            try:
                write_api.write(bucket=bucket, record=points)
                logger.info(f"Successfully wrote {len(points)} points to bucket {bucket}.")
            except Exception as e:
                logger.error(f"Failed to write {len(points)} points to bucket {bucket}: {str(e)}. Re-adding to queue.")
                failed_writes_queue.put((bucket, points))
                break  # Exit loop if a write fails
    except Exception as e:
        logger.error(f"Error during retrying failed writes: {str(e)}. Reconnecting to InfluxDB.")
        influxdb_client, write_api = connect_influxdb()

def update_weather_data():
    """Fetch and store current weather data."""
    if not WEATHER_CONFIG["enabled"]:
        return

    try:
        temperature, weather_description, precipitation_float = get_weather()
        timestamp = datetime.utcnow()

        weather_data = {
            "measurement": "weather_data",
            "tags": {"location": WEATHER_CONFIG['location']},
            "time": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fields": {
                "temperature": temperature,
                "weather_description": weather_description,
                "precipitation": precipitation_float
            }
        }
        try:
            if INFLUXDB_CONFIG["enabled"]:
                write_api.write(bucket=INFLUXDB_CONFIG['bucket'], record=weather_data)
                logger.info(f"Weather data written to bucket: {weather_data}")

            # Publish to MQTT
            state_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/weather_data/state"
            payload = json.dumps(weather_data['fields'])
            send_to_mqtt(state_topic, payload)

        except Exception as e:
            logger.error(f"Failed to write weather data to InfluxDB: {str(e)}. Adding to queue.")
            failed_writes_queue.put((INFLUXDB_CONFIG['bucket'], [weather_data]))
    except Exception as e:
        logger.error(f"Failed to fetch weather data: {str(e)}")

def update_traffic_data():
    if not TELRAAM_API_CONFIG["enabled"]:
        return

    logger.info("update_traffic_data function called")
    logger.info("Starting traffic data update")

    # Fetch hourly data for the current hour
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    end_time = now.replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(hours=1)
    time_start = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    time_end = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fetch hourly data for the current hour
    hourly_data = fetch_traffic_data_with_retries(
        TELRAAM_API_CONFIG["segment_id"], time_start, time_end,
        TELRAAM_API_CONFIG["api_key"], "per-hour"
    )
    if hourly_data:
        store_traffic_data_in_influxdb(hourly_data, write_api)
        logger.info(f"Hourly traffic data updated from {time_start} to {time_end}")
    else:
        logger.warning("No hourly traffic data fetched")

    # Recalculate time_start for the last 24 hours
    start_time_24h = end_time - timedelta(hours=24)
    time_start_24h = start_time_24h.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Fetch last 24 hours hourly data for daily aggregation
    hourly_data_last_day = fetch_traffic_data_with_retries(
        TELRAAM_API_CONFIG["segment_id"], time_start_24h, time_end,
        TELRAAM_API_CONFIG["api_key"], "per-hour"
    )
    if hourly_data_last_day:
        daily_totals = aggregate_hourly_to_daily(hourly_data_last_day)
        store_traffic_data_in_influxdb([daily_totals], write_api)
        logger.info(f"Daily traffic data updated for {daily_totals['date']}")
    else:
        logger.warning("No daily traffic data fetched")

    logger.info("Traffic data update completed")

def update_noise_level():
    """Monitor noise levels, record events, and perform actions based on configured thresholds."""
    window_start_time = time.time()
    current_peak_dB = 0
    peak_temperature = None
    peak_weather_description = ""
    peak_precipitation_float = 0.0

    global dev
    dev = detect_usb_device()
    if dev is None:
        logger.error("USB sound meter device not found")
    else:
        logger.info("USB sound meter device connected")

    while True:
        current_time = time.time()
        if current_time - window_start_time >= DEVICE_AND_NOISE_MONITORING_CONFIG['time_window_duration']:
            timestamp = datetime.utcnow()
            delete_old_images()

            # Publish real-time noise level
            realtime_data = [{
                "measurement": "noise_buster_events",
                "tags": {"location": "noise_buster"},
                "time": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": {"noise_level": round(current_peak_dB, 1)}
            }]
            try:
                if INFLUXDB_CONFIG["enabled"]:
                    write_api.write(bucket=INFLUXDB_CONFIG['realtime_bucket'], record=realtime_data)
                    logger.info(f"All noise levels written to realtime bucket: {round(current_peak_dB, 1)} dB")

                # Publish to MQTT for all readings
                realtime_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/realtime_noise_levels/state"
                realtime_payload = json.dumps(realtime_data[0]['fields'])
                send_to_mqtt(realtime_topic, realtime_payload)

            except Exception as e:
                logger.error(f"Failed to write to InfluxDB: {str(e)}. Adding to queue.")
                failed_writes_queue.put((INFLUXDB_CONFIG['realtime_bucket'], [realtime_data]))

            if current_peak_dB >= DEVICE_AND_NOISE_MONITORING_CONFIG['minimum_noise_level']:
                peak_temperature_float = float(peak_temperature) if peak_temperature is not None else 0.0
                peak_weather_description_adjusted = peak_weather_description if peak_weather_description is not None else ""
                main_data = {
                    "measurement": "noise_buster_events",
                    "tags": {"location": "noise_buster"},
                    "time": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "fields": {
                        "noise_level": round(current_peak_dB, 1),
                        "temperature": peak_temperature_float,
                        "weather_description": peak_weather_description_adjusted,
                        "precipitation_float": peak_precipitation_float
                    }
                }
                try:
                    if INFLUXDB_CONFIG["enabled"]:
                        write_api.write(bucket=INFLUXDB_CONFIG['bucket'], record=main_data)
                        logger.info(f"High noise level data written to main bucket: {main_data}")

                    # Publish to MQTT for events exceeding the threshold
                    event_topic = f"homeassistant/sensor/{DEVICE_AND_NOISE_MONITORING_CONFIG['device_name']}/noise_levels/state"
                    event_payload = json.dumps(main_data['fields'])
                    send_to_mqtt(event_topic, event_payload)

                except Exception as e:
                    logger.error(f"Failed to write to InfluxDB: {str(e)}. Adding to queue.")
                    failed_writes_queue.put((INFLUXDB_CONFIG['bucket'], [main_data]))

                capture_image(current_peak_dB, peak_temperature_float, peak_weather_description_adjusted, peak_precipitation_float, timestamp)

            window_start_time = current_time
            current_peak_dB = 0
            peak_temperature = None
            peak_weather_description = ""
            peak_precipitation_float = 0.0

        # Read current noise level from the device
        try:
            if dev:
                ret = dev.ctrl_transfer(0xC0, 4, 0, 0, 200)
                dB = (ret[0] + ((ret[1] & 3) * 256)) * 0.1 + 30
                if dB > current_peak_dB:
                    current_peak_dB = dB
                    peak_temperature, peak_weather_description, precipitation = get_weather()
                    peak_precipitation_float = float(precipitation)
            else:
                logger.error("USB device not available")
        except usb.core.USBError as usb_err:
            logger.error(f"USB Error reading from device: {str(usb_err)}")
            dev = detect_usb_device()
            if dev is None:
                logger.error("Device not found on re-scan")
            else:
                logger.info("Reconnected to USB device")
        except Exception as e:
            logger.error(f"Unexpected error reading from device: {str(e)}")

        time.sleep(0.1)

def schedule_tasks():
    try:
        if TELRAAM_API_CONFIG["enabled"]:
            interval = TELRAAM_API_CONFIG["request_interval_minutes"]
            schedule.every(interval).minutes.do(update_traffic_data)
            logger.info(f"Telraam API Call Tasks have been scheduled successfully to run every {interval} minutes.")

        # Schedule weather data update every 5 minutes
        if WEATHER_CONFIG["enabled"]:
            schedule.every(5).minutes.do(update_weather_data)
            logger.info("Weather data update task has been scheduled to run every 5 minutes.")

        # Schedule retry of failed writes every minute if InfluxDB is enabled
        if INFLUXDB_CONFIG["enabled"]:
            schedule.every(1).minute.do(retry_failed_writes)
    except Exception as e:
        logger.error("Error scheduling tasks: " + str(e))
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        dev = detect_usb_device()
        if dev is None:
            raise ValueError("Device not found")
        logger.info("Starting Noise Monitoring")
        if PUSHOVER_CONFIG["enabled"]:
            send_pushover_notification("Noise Buster has started monitoring.")
        notify_on_start()

        # Initialize the noise monitoring in a separate thread
        noise_monitoring_thread = threading.Thread(target=update_noise_level)
        noise_monitoring_thread.daemon = True
        noise_monitoring_thread.start()

        if INFLUXDB_CONFIG["enabled"]:
            influxdb_client, write_api = connect_influxdb()
        if TELRAAM_API_CONFIG["enabled"]:
            update_traffic_data()
        if WEATHER_CONFIG["enabled"]:
            update_weather_data()  # Initial weather data update
        schedule_tasks()
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Manual interruption by user.")
    except Exception as e:
        with open('error.log', 'a') as f:
            f.write(str(e) + "\n")
            f.write(traceback.format_exc())
        if PUSHOVER_CONFIG["enabled"]:
            send_pushover_notification(f"Noise Buster encountered an error: {str(e)}")
        logger.error(str(e))
        logger.error(traceback.format_exc())
