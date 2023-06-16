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
influxdb_host = "192.168.194.240"  # Set the InfluxDB host address (e.g., "192.168.194.240")
influxdb_port = 8086  # Set the InfluxDB port (default: 8086)
influxdb_token = "YPXMtL0czD5iIm_r4tPBTbdWEwVGPMjVZFgPT4deo9PApB5ig04BfE9vNM-k2gK2jw3VU7iWw84kNVw4CYtCdA=="  # Set the InfluxDB token (within double quotes)
influxdb_org = "montefiore"  # Set the InfluxDB organization name (e.g., "montefiore")
influxdb_bucket = "montefiore"  # Set the InfluxDB bucket name (e.g., "montefiore")
influxdb_timeout = 20000  # Set the InfluxDB timeout value in milliseconds (e.g., 20000)

# Pushover connection information (Optional)
pushover_user_key = "u8pztbghz47d689h8nwsctga1jp7z1"  # Set the Pushover user key (within double quotes) or leave empty to skip Pushover notifications
pushover_api_token = "a3wra1jajpsw663hqvkdpyfspfr8pq"  # Set the Pushover API token (within double quotes) or leave empty to skip Pushover notifications

# Minimum noise level for logging events
minimum_noise_level = 80  # Set the minimum noise level for logging events (e.g., 80)

# Content of messages sent by Pushover (comment if you do not use pushover or don't want notifications to be sent)
pushover_message = "Let's catch these noisy motorcycles and trucks"  # Set the content of the Pushover message (within double quotes)
pushover_title = "Noise monitoring Montefiore"  # Set the title of the Pushover message (within double quotes)

# Message to display when starting the script
start_message = "Let's listen to our noisy bikers and truckers"  # Set the start message to display (within double quotes)

# InfluxDB measurement and location
influxdb_measurement = "noise_levels_montefiore_influxdb"  # Set the InfluxDB measurement name (within double quotes)
influxdb_location = "Montefiore"  # Set the location for InfluxDB measurement (within double quotes)

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
