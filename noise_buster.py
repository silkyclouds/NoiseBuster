import logging
import sys
import usb.core
import time
import traceback
from datetime import datetime
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from pushover import Client

# Configure logging level and output format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create a logger
logger = logging.getLogger(__name__)

# --------------------- Configuration Section ---------------------

# InfluxDB host address (IP or URL)
influxdb_host = "192.168.194.240"
# InfluxDB port (usually 8086)
influxdb_port = 8086
# InfluxDB authentication token
influxdb_token = "Your InfluxDB Token Here"
# InfluxDB organization name
influxdb_org = "noise_buster"
# InfluxDB bucket name
influxdb_bucket = "noise_buster"
# InfluxDB timeout in milliseconds
influxdb_timeout = 20000

# Pushover user key for notifications (leave empty to disable Pushover notifications)
pushover_user_key = "Your Pushover User Key Here"
# Pushover API token (leave empty to disable Pushover notifications)
pushover_api_token = "Your Pushover API Token Here"

# Minimum noise level for logging events (in dB)
minimum_noise_level = 80

# Message content for Pushover notifications
pushover_message = "Lets bust these noise events"
# Title for Pushover notifications
pushover_title = "Noise Buster"

# Message to display when starting the script
start_message = "Huray, Noise Buster started"

# InfluxDB measurement name (where data will be written in the DB)
influxdb_measurement = "noise_buster_events"
# Location tag for InfluxDB measurement
influxdb_location = "noise_buster"

# dB adjustment for distance (in dB) (if you happen to put your volume meter far away from the noise source, you can add dB's here to reflect a closer reality)
dB_adjustment = 1

# --------------------- End of Configuration Section ---------------------

# Counter for failed InfluxDB pings
failed_influxdb_pings = 0

# Last recorded dB and timestamp
last_dB = None
last_timestamp = None

# Function to check the health of the InfluxDB server
def check_influxdb_health():
    global failed_influxdb_pings
    try:
        if influxdb_client.health():
            failed_influxdb_pings = 0
        else:
            failed_influxdb_pings += 1
    except Exception as e:
        failed_influxdb_pings += 1

    if failed_influxdb_pings >= 10:
        message = "InfluxDB server is down. Failed to respond to 10 consecutive pings."
        if pushover_user_key and pushover_api_token:
            client.send_message(message, title=pushover_title)
        logger.info(message)
        failed_influxdb_pings = 0

    time.sleep(5)

# Function to update noise level and log it
def update():
    global last_dB, last_timestamp
    while True:
        ret = dev.ctrl_transfer(0xC0, 4, 0, 0, 200)
        global dB
        dB = (ret[0] + ((ret[1] & 3) * 256)) * 0.1 + 30
        dB += dB_adjustment  # Apply dB adjustment based on distance
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        if dB >= minimum_noise_level and (dB != last_dB or timestamp != last_timestamp):
            last_dB = dB
            last_timestamp = timestamp
            logger.info('%s, %.1f dB', timestamp, round(dB, 1))

            data = [
                {
                    "measurement": influxdb_measurement,
                    "tags": {
                        "location": influxdb_location
                    },
                    "time": timestamp,
                    "fields": {
                        "level": round(dB, 1)
                    }
                }
            ]
            write_api.write(influxdb_bucket, record=data)

            # Log data to CSV
            with open('noise.csv', 'a') as f:
                f.write(f"{timestamp},{round(dB, 1)}\n")

        time.sleep(0.5)

try:
    if pushover_user_key and pushover_api_token:
        client = Client(pushover_user_key, api_token=pushover_api_token)
        client.send_message(pushover_message, title=pushover_title)

    dev = usb.core.find(idVendor=0x16c0, idProduct=0x5dc)

    dB = 0

    logger.info(start_message)

    influxdb_client = InfluxDBClient(url=f"http://{influxdb_host}:{influxdb_port}", token=influxdb_token,
                                     org=influxdb_org, timeout=influxdb_timeout)
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

    if influxdb_client.health():
        logger.info("Connected to InfluxDB successfully.")
        if pushover_user_key and pushover_api_token:
            client.send_message("Successfully connected to InfluxDB", title=pushover_title)
    else:
        logger.info("Error connecting to InfluxDB.")
        if pushover_user_key and pushover_api_token:
            client.send_message("Error connecting to InfluxDB", title=pushover_title)

    # Start the InfluxDB server health check in a separate thread
    from threading import Thread
    Thread(target=check_influxdb_health).start()

    # Start updating noise level
    update()
except Exception as e:
    with open('error.log', 'a') as f:
        f.write(str(e) + "\n")
        f.write(traceback.format_exc())
        logger.error(str(e))
        logger.error(traceback.format_exc())
