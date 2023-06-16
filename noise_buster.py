import logging
import sys
import usb.core
import sched
import time
import logging
import traceback

from threading import Timer
from datetime import datetime
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from pushover import Client

# Configurer le niveau de journalisation et la sortie des journaux
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Créer un logger
logger = logging.getLogger(__name__)

##############################################################################
#CONFIGUE THE BELOW SETTINGS TO YOUR CONVENIENCE
##############################################################################

# InfluxDB connection information
influxdb_host = "127.0.0.1"  # Set the InfluxDB host address (e.g., "192.168.194.240")
influxdb_port = 8086  # Set the InfluxDB port (default: 8086)
influxdb_token = ""  # Set the InfluxDB token (within double quotes)
influxdb_org = "noise_buster"  # Set the InfluxDB organization name (e.g., "montefiore")
influxdb_bucket = "noise_buster"  # Set the InfluxDB bucket name (e.g., "montefiore")
influxdb_timeout = 20000  # Set the InfluxDB timeout value in milliseconds (e.g., 20000)

# Pushover connection information (Optional) (uncomment if you want to use pushover!)
#pushover_user_key = "your_pushover_key_here"  # Set the Pushover user key (within double quotes) or leave empty to skip Pushover notifications
#pushover_api_token = "your_pushover_api_token_here"  # Set the Pushover API token (within double quotes) or leave empty to skip Pushover notifications

# Minimum noise level for logging events
minimum_noise_level = 80  # Set the minimum noise level for logging events (e.g., 80)

# Content of messages sent by Pushover (uncomment if you want to use pushover)
#pushover_message = "Lets bust these noise events"  # Set the content of the Pushover message (within double quotes)
#pushover_title = "Noise Buster"  # Set the title of the Pushover message (within double quotes)

# Message to display when starting the script
start_message = "Lets bust these noise events"  # Set the start message to display (within double quotes)

# InfluxDB measurement and location
influxdb_measurement = "noise_buster_events"  # Set the InfluxDB measurement name (within double quotes)
influxdb_location = "noise_buster"  # Set the location for InfluxDB measurement (within double quotes)

##############################################################################
# DO NOT TOUCH ANYTHING BELOW THIS LINE (EXCEPT IF YOU KNOW WHAT YOU ARE DOING)
##############################################################################


# Créer un gestionnaire de journalisation pour la sortie standard
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
stdout_handler.setFormatter(stdout_formatter)

# Créer un logger pour la sortie standard
stdout_logger = logging.getLogger('stdout_logger')
stdout_logger.setLevel(logging.INFO)
stdout_logger.addHandler(stdout_handler)

try:
    if pushover_user_key and pushover_api_token:
        client = Client(pushover_user_key, api_token=pushover_api_token)
        client.send_message(pushover_message, title=pushover_title)

    dev = usb.core.find(idVendor=0x16c0, idProduct=0x5dc)

    dB = 0

    stdout_logger.info(start_message)

    # Connect to InfluxDB
    influxdb_client = InfluxDBClient(url=f"http://{influxdb_host}:{influxdb_port}", token=influxdb_token,
                                     org=influxdb_org, timeout=influxdb_timeout)
    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

    if influxdb_client.health():
        stdout_logger.info("Connected to InfluxDB successfully.")
        if pushover_user_key and pushover_api_token:
            client.send_message("Successfully connected to InfluxDB", title=pushover_title)
    else:
        stdout_logger.info("Error connecting to InfluxDB.")
        if pushover_user_key and pushover_api_token:
            client.send_message("Error connecting to InfluxDB", title=pushover_title)

    # Update noise level data
    def update():
        ret = dev.ctrl_transfer(0xC0, 4, 0, 0, 200)
        global dB
        dB = (ret[0] + ((ret[1] & 3) * 256)) * 0.1 + 30
        if dB >= minimum_noise_level:
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            stdout_logger.info('%s, %.1f dB', timestamp, round(dB, 1))

            # Write data to InfluxDB
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

        t = Timer(0.5, update)
        t.start()

    # Start the update loop
    update()
except Exception as e:
   with open('error.log', 'a') as f:
        f.write(str(e) + "\n")
        f.write(traceback.format_exc())
        logger.error(str(e))
        logger.error(traceback.format_exc())
