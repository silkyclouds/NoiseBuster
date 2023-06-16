# NoiseBuster

NoiseBuster is a simple Python script that utilizes the USB library to interact with a sound meter device and catalog the recorded noise events. The script provides basic functionalities for managing and monitoring noise levels.



## Features

- Noise Recording: The script interfaces with a compatible sound meter device connected via USB and records noise events, capturing information such as noise levels and timestamps.

- Data Storage: Recorded noise events are stored locally in a structured format, allowing easy retrieval and analysis of noise data. The script includes the required influxDB modules to allow you to inject the events in your own influxDB. 

## Getting Started

### Prerequisites

Before using NoiseBuster, ensure the following prerequisites are met:

- Python 3.x is installed on your system.
- The necessary Python dependencies are installed. See the `requirements.txt` file for a list of dependencies.
- Optional (but you want this) -> make sure you have a running instance of influxDB 2.x, and created a bucket dedicated to the noise monitoring)
- Optional -> the script includes a pushover module, allowing you to get notified when the script starts and connects to influxDB

### Installation

1. Clone the NoiseBuster repository from GitHub using the following command : git clone https://github.com/your-username/noise_buster.git
2. Install a recent version of setuptools as older versions prevents to successfully install dependencies: pip install -r setuptools.txt
3. Install the requirements : pip install -r requirements.txt

## Configuration

Before running the script, you need to configure the necessary information. Open the `noise_buster.py` file in a text editor and locate the following section:

```
# InfluxDB connection information
influxdb_host = ""  # Set the InfluxDB host address (e.g., "192.168.194.240")
influxdb_port = 8086  # Set the InfluxDB port (default: 8086)
influxdb_token = "your_api_key_comes_here"  # Set the InfluxDB token (within double quotes)
influxdb_org = "organization_name"  # Set the InfluxDB organization name (e.g., "montefiore")
influxdb_bucket = "bucket_name"  # Set the InfluxDB bucket name (e.g., "montefiore")
influxdb_timeout = 20000  # Set the InfluxDB timeout value in milliseconds (value is in milliseconds, try a higher value if you encounter timeouts) (e.g., 20000)

# Pushover connection information (Optional) (comment if not wanted)
pushover_user_key = "pushover_user_key"  # Set the Pushover user key (within double quotes) or leave empty to skip Pushover notifications
pushover_api_token = "pushover_api_token"  # Set the Pushover API token (within double quotes) or leave empty to skip Pushover notifications

# Minimum noise level for logging events
minimum_noise_level = 80  # Set the minimum noise level for logging events (e.g., 80)

# Content of messages sent by Pushover (comment if you do not use pushover or don't want notifications to be sent)
pushover_message = "Lets bust these noise events"  # Set the content of the Pushover message (within double quotes)
pushover_title = "Noise Buster"  # Set the title of the Pushover message (within double quotes)

# Message to display when starting the script
start_message = "Lets bust these noise events"  # Set the start message to display (within double quotes)

# InfluxDB measurement and location
influxdb_measurement = "noise_levels_events"  # Set the InfluxDB measurement name (within double quotes)
influxdb_location = "noise_buster"  # Set the location for InfluxDB measurement (within double quotes)
````

### Running the script
1. connect your USB monitoring device to your computer (yes, I had to write this down)
2. execute the script : python noise_buster.py

From now on, you should be able to query your influxDB and see the noise events coming in ! 

### Tips and tricks
- You can easily check if the script is recording events by simply runing it and start screaming (be creative, scream something funny). As soon the dB level you configured will be readhed, you'll see events like this showing up : 2023-06-16 12:55:58,883 - INFO - 2023-06-16T10:55:58Z, 89.1 dB

- For some reason, the script is not running outside of a venv on my end. If this is also happening to you, try the following : 
```
python3 -m pip install --user virtualenv
python3 -m venv env
source env/bin/activate
pip install -r setuptools.txt && pip install -r requirements.txt
python noise_buster.py
````
### Contributing
Contributions to noise_buster.py are welcome! If you encounter issues, have suggestions, or would like to add new features, please submit an issue or create a pull request on the GitHub repository.

### License
This project is licensed under the GNU License. 

### Project
The initial project is a project by Raphael Vael




