<p align="center">
  <img src="noisebuster.png" alt="NoiseBuster Logo">
</p>


NoiseBuster

NoiseBuster is an advanced Python application designed to monitor and log noise levels using a USB-connected sound meter. It not only records noise events but also integrates with various services like InfluxDB, MQTT, Discord, and more to provide a comprehensive noise monitoring solution. With features like weather data integration and traffic data collection, NoiseBuster offers a versatile tool for environmental monitoring and analysis.

Screenshot of the Grafana dashboard displaying noise events and analytics.

Screenshot of Home Assistant displaying noise levels via MQTT integration.

Table of Contents

	•	Features
	•	Usage
	•	Getting Started
	•	Prerequisites
	•	Installation
	•	Hardware Requirements
	•	Configuration
	•	Running the Script
	•	Using Docker (Recommended)
	•	Using Python Directly
	•	Home Assistant Integration
	•	InfluxDB and Grafana Setup
	•	Tips and Tricks
	•	Additional Resources
	•	Contributing
	•	Next Steps
	•	License
	•	Project

Features

	•	Noise Monitoring: Interfaces with a USB sound meter to monitor and record noise levels in real-time.
	•	Data Storage: Stores recorded noise events in InfluxDB for easy retrieval and analysis.
	•	MQTT Integration (Optional): Publishes noise levels and events to an MQTT broker for integration with home automation systems like Home Assistant.
	•	Weather Data Collection (Optional): Fetches current weather data from OpenWeatherMap API to correlate noise events with weather conditions.
	•	Traffic Data Collection (Optional): Integrates with Telraam API to collect traffic data, allowing analysis of noise levels in relation to traffic conditions.
	•	Note: A dedicated YOLO-powered traffic counting script is in development and will be available soon.
	•	Image Capture (Optional): Captures images using an IP camera or Raspberry Pi camera when noise levels exceed a specified threshold.
	•	Notifications (Optional): Sends notifications via Discord and Pushover when certain events occur (e.g., high noise levels, API failures).
	•	Configurable Timezone: Adjusts timestamps according to the specified timezone offset.
	•	Error Handling and Logging: Robust error handling with detailed logging for troubleshooting.

Usage

	•	Monitor loud traffic, planes, live events, and more.
	•	Create insightful graphics to share statistics with authorities.
	•	Analyze environmental noise in correlation with weather and traffic data.

Getting Started

Prerequisites

Before using NoiseBuster, ensure the following prerequisites are met:

	•	Operating System: Linux-based system (e.g., Ubuntu, Debian, Raspberry Pi OS).
	•	Python: Python 3.6 or higher installed.
	•	USB Sound Meter: A USB-connected sound level meter. All models with USB communication capabilities should work.
	•	Other types like RS485 models and ESP devices with calibrated microphones could be used but may require additional setup by the user.
	•	Internet Connection: Required for API integrations (e.g., OpenWeatherMap, Telraam).
	•	Optional but Recommended:
	•	InfluxDB 2.x: For data storage and analysis.
	•	Grafana: For data visualization.
	•	Optional:
	•	MQTT Broker: If you wish to publish data to an MQTT broker.
	•	Docker: For containerized deployment.

Installation

	1.	Clone the NoiseBuster repository from GitHub:

git clone https://github.com/silkyclouds/NoiseBuster.git


	2.	Navigate to the directory:

cd NoiseBuster


	3.	Create a virtual environment (recommended):

python3 -m venv env
source env/bin/activate


	4.	Install the requirements:

pip install --upgrade pip
pip install -r requirements.txt



Hardware Requirements

	•	USB Sound Meter:
	•	The application is designed to work with USB-connected sound level meters.
	•	Example Device:

This is the USB sound level meter used for testing.
	•	USB Sound Level Meter on AliExpress

	•	Ensure the device supports USB communication.
	•	For devices not automatically detected, you may need to specify the USB vendor ID and product ID in the configuration. Use the lsusb command to find these IDs.

	•	Camera (Optional):
	•	IP Camera:
	•	Supports RTSP or HTTP protocols.
	•	Provide the camera’s URL in the configuration.
	•	Raspberry Pi Camera:
	•	Connects directly to the Raspberry Pi.
	•	Requires the picamera library.

Configuration

All configuration settings are stored in the config.json file. Here is how to set up your configuration:

	1.	Open config.json in a text editor. Keep all default IP addresses as localhost or 127.0.0.1 to ensure it works out of the box.
	2.	Configure each section:
	•	InfluxDB Configuration:
	•	Set "enabled": true to store data in InfluxDB.
	•	Provide your InfluxDB host, port, token, org, and bucket names.
	•	Ensure you create buckets named exactly as in the config sample ("noise_buster" and "noise_buster_realtime") unless you know what you’re doing.
	•	Important: If you’re new to InfluxDB, follow the official InfluxDB setup guide to create your organization, buckets, and API tokens.
	•	Pushover Configuration (Optional):
	•	Set "enabled": true to receive Pushover notifications.
	•	Provide your user_key and api_token. Sign up at Pushover.
	•	Weather Configuration (Optional):
	•	Set "enabled": true to fetch weather data.
	•	Provide your OpenWeatherMap api_key and location. Sign up at OpenWeatherMap API.
	•	MQTT Configuration (Optional):
	•	Set "enabled": true to publish data to an MQTT broker.
	•	Provide your MQTT server, port, user, and password. Learn more about MQTT at mqtt.org.
	•	Camera Configuration (Optional):
	•	Set "use_ip_camera": true or "use_pi_camera": true depending on your setup.
	•	Provide the ip_camera_url if using an IP camera.
	•	Device and Noise Monitoring Configuration:
	•	Set device_name for identification.
	•	Set minimum_noise_level in decibels to trigger events.
	•	Specify image_save_path where images will be stored.
	•	Provide usb_vendor_id and usb_product_id if automatic USB device detection fails. Use lsusb to find these IDs.
	•	Telraam API Configuration (Optional):
	•	Set "enabled": true to collect traffic data.
	•	Provide your Telraam api_key and segment_id. Learn more at Telraam.
	•	Note: A dedicated YOLO-powered traffic counting script is in development and will be available soon.
	•	Timezone Configuration:
	•	Set timezone_offset relative to UTC.
	•	Discord Configuration (Optional):
	•	Set "enabled": true to send notifications to Discord.
	•	Provide your Discord webhook_url. Create one at Discord Webhooks.
	3.	Save config.json.

Running the Script

Using Docker (Recommended)

The easiest way to get started is by using Docker. A docker-compose.yml file is provided to set up all the necessary components.

	1.	Ensure Docker and Docker Compose are installed on your system. Learn more at Docker Installation.
	2.	Navigate to the project directory:

cd NoiseBuster


	3.	Build the Docker image:

docker build -t noisebuster .


	4.	Pass the USB device to the Docker container:
	1.	List your USB devices using the lsusb command:

lsusb


	2.	Identify your USB sound meter in the list.
	3.	Note the Bus and Device IDs (e.g., Bus 003 Device 011).
	4.	Run the Docker container, passing the USB device:

docker run -d --name noisebuster --device=/dev/bus/usb/003/011 noisebuster

Replace /dev/bus/usb/003/011 with your own Bus and Device IDs.

	5.	Alternatively, use docker-compose.yml:

version: '3'
services:
  noisebuster:
    image: noisebuster
    container_name: noisebuster
    restart: always
    volumes:
      - ./config.json:/app/config.json
      - ./images:/app/images
    devices:
      - "/dev/bus/usb/003/011:/dev/bus/usb/003/011"
    environment:
      - TZ=UTC

Make sure to adjust the devices section with your USB device path.

	6.	Run Docker Compose:

docker-compose up -d


	7.	Check the logs to ensure it’s running correctly:

docker-compose logs -f



Using Python Directly

	1.	Ensure the USB sound meter is connected to your computer.
	2.	Activate the virtual environment if you created one:

source env/bin/activate


	3.	Run the application:

python noisebuster.py



Home Assistant Integration

To display noise levels and other data as entities in Home Assistant via MQTT, you need to add the following configuration to your configuration.yaml file:

mqtt:
  sensor:
    - name: "Noise Buster Traffic Realtime Noise Level"
      state_topic: "homeassistant/sensor/noise_buster_traffic/realtime_noise_levels/state"
      value_template: "{{ value_json.noise_level }}"
      unit_of_measurement: "dB"

    - name: "Noise Buster Traffic Noise Level"
      state_topic: "homeassistant/sensor/noise_buster_traffic/noise_levels/state"
      value_template: "{{ value_json.noise_level }}"
      unit_of_measurement: "dB"

    - name: "Noise Buster Traffic Weather Data"
      state_topic: "homeassistant/sensor/noise_buster_traffic/weather_data/state"
      value_template: "{{ value_json.temperature }}"
      unit_of_measurement: "°C"
      json_attributes_topic: "homeassistant/sensor/noise_buster_traffic/weather_data/state"
      json_attributes_template: "{{ value_json | tojson }}"

    - name: "Noise Buster Traffic Data"
      state_topic: "homeassistant/sensor/noise_buster_traffic/traffic_data/state"
      value_template: "{{ value_json.car }}"
      unit_of_measurement: "vehicles"
      json_attributes_topic: "homeassistant/sensor/noise_buster_traffic/traffic_data/state"
      json_attributes_template: "{{ value_json | tojson }}"

InfluxDB and Grafana Setup

To visualize and analyze the data collected by NoiseBuster, set up InfluxDB and Grafana.

InfluxDB Setup

	1.	Install InfluxDB. Follow the official InfluxDB installation guide.
	2.	Create buckets named exactly as in the config sample:
	•	noise_buster
	•	noise_buster_realtime
	3.	Generate an API token with write access to these buckets.
	4.	Update config.json with your InfluxDB details.

Grafana Setup

	1.	Install Grafana. Follow the official Grafana installation guide.
	2.	Add InfluxDB as a data source using the same credentials as in config.json.
	3.	Import the provided Grafana dashboard JSON files to start monitoring your events quickly.
	•	The Grafana dashboard JSON files are included in the repository for your convenience.
	4.	Adjust queries if you have different measurement names or tags.
	5.	Visualize Data:
	•	Start exploring your data and customize the dashboard as needed.

Tips and Tricks

	•	Testing Noise Events:
	•	To test the setup, generate a loud noise near the sound meter.
	•	Check the logs or your InfluxDB to see if the event was recorded.
	•	Example log output:

2023-06-16 12:55:58,883 - INFO - All noise levels written to realtime bucket: 89.1 dB


	•	Virtual Environment Issues:
	•	If you encounter issues running the script, ensure you are in the virtual environment.
	•	Activate it using:

source env/bin/activate


	•	Device Detection:
	•	If the USB sound meter is not detected, specify usb_vendor_id and usb_product_id in config.json.
	•	Use the lsusb command to find these IDs.
	•	Feature Enabling/Disabling:
	•	Many features like Pushover notifications, weather data, MQTT, and Telraam integration are optional.
	•	Enable or disable them in the config.json file as needed.
	•	Using Other Hardware:
	•	While the application is designed for USB sound meters, other types like RS485 models and ESP devices with calibrated microphones could be used but may require additional setup and modifications to the code.

Additional Resources

	•	Pushover: https://pushover.net/ - Service for receiving push notifications.
	•	Discord: https://discord.com/ - Communication platform with webhook support for notifications.
	•	OpenWeatherMap API: https://openweathermap.org/api - Service for fetching current weather data.
	•	MQTT: https://mqtt.org/ - Lightweight messaging protocol for small sensors and mobile devices.
	•	Telraam: https://telraam.net/ - Platform for collecting traffic data.
	•	InfluxDB: https://www.influxdata.com/ - Time series database for storing monitoring data.
	•	Grafana: https://grafana.com/ - Open-source platform for data visualization.

Contributing

Contributions are welcome! If you encounter issues, have suggestions, or would like to add new features:

	1.	Fork the repository.
	2.	Create a new branch for your changes.
	3.	Submit a pull request with a detailed explanation of your changes.

Next Steps

	•	Adding Vehicle Detection:
	•	Implementing OpenCV to correlate noise events with specific vehicles.
	•	Centralized InfluxDB Instance:
	•	Providing a centralized InfluxDB instance for users to contribute data.
	•	Hardware Expansion:
	•	Investigating other hardware options like ESP devices for sound monitoring.
	•	Data Retention Strategies:
	•	Implementing better data retention policies to manage database size.
	•	YOLO-powered Traffic Counting:
	•	A dedicated YOLO-powered traffic counting script is in development and will be available soon.

License

This project is licensed under the GNU License.

Project

The initial project is a project by Raphael Vael.

requirements.txt

aiohttp==3.8.1
aiosignal==1.2.0
async-timeout==4.0.2
attrs==21.4.0
base58==2.1.1
certifi==2022.5.18.1
cffi==1.15.0
chardet==4.0.0
charset-normalizer==2.0.12
click==8.1.3
colorama==0.4.4
cryptography==36.0.2
frozenlist==1.3.0
idna==3.3
influxdb-client==1.32.0
multidict==6.0.2
pipreqs==0.4.11
pycparser==2.21
PyJWT==2.4.0
pyOpenSSL==22.0.0
PySocks==1.7.1
python-dateutil==2.8.2
pytz==2022.1
requests==2.27.1
rsa==4.8
schedule==1.1.0
six==1.16.0
urllib3==1.26.9
yarl==1.7.2
paho-mqtt==1.6.1
picamera==1.13
opencv-python==4.5.5.64
numpy==1.21.6
usb==1.1.2

Please feel free to copy and paste the content into your GitHub repository’s README file. All code sections are properly formatted for easy copying and pasting.

If you have any questions or need further assistance, don’t hesitate to ask!
