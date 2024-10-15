<!DOCTYPE html>
<html>
<head>
</head>
<body>

<p align="center">
  <img src="noisebuster.png" alt="NoiseBuster Logo">
</p>

<p>
NoiseBuster is an advanced Python application designed to monitor and log noise levels using a USB-connected sound meter. It not only records noise events but also integrates with various services like InfluxDB, MQTT, Discord, and more to provide a comprehensive noise monitoring solution. With features like weather data integration and traffic data collection, NoiseBuster offers a versatile tool for environmental monitoring and analysis.
</p>

<h2 align="center" style="margin-top: 20px;">Live NoiseBuster Running Instance</h2>
<p align="center" style="font-size: 1.75em; margin-top: 10px;">
  <strong>
    <a href="https://nb-be-mont-1.noisebuster.ovh/public-dashboards/3f841065ea804f11847a85ebd5e0c0d5?orgId=1&refresh=5s" target="_blank" style="text-decoration: none; color: #ff4500;">
      🚀 Click here to see NoiseBuster in action!
    </a>
  </strong>
</p>

<p align="center">
  <img src="noisebuster_grafana.png" alt="NoiseBuster Dashboard">
  <br>
  <em>NoiseBuster Dashboard in Grafana showing noise events over time.</em>
</p>
<p align="center">
  <img src="noisebuster_home_assistant.png" alt="NoiseBuster Analytics">
  <br>
  <em>Analysis of noise levels in Home Assistant.</em>
</p>

<hr>

<h2>Important Notice</h2>
<p><strong>Note:</strong> NoiseBuster is licensed under the Creative Commons Attribution-NonCommercial (CC BY-NC) License, which means it is free for non-commercial use only. Commercial use requires explicit permission from the project owner. For details, visit the <a href="https://creativecommons.org/licenses/by-nc/4.0/">CC BY-NC License page</a>.</p>

<h2>Discord Server</h2>

<p>
Join the community on our Discord server to discuss, contribute, and get support: <a href="https://discord.gg/pCxtsg7mBN">NoiseBuster Discord Server</a>
</p>

<h2>Features</h2>

<ul>
    <li><strong>Noise Monitoring:</strong> Interfaces with a USB sound meter to monitor and record noise levels in real-time.</li>
    <li><strong>Data Storage:</strong> Stores recorded noise events in InfluxDB for easy retrieval and analysis.</li>
    <li><strong>MQTT Integration (<em>Optional</em>):</strong> Publishes noise levels and events to an MQTT broker for integration with home automation systems like Home Assistant.</li>
    <li><strong>Weather Data Collection (<em>Optional</em>):</strong> Fetches current weather data from OpenWeatherMap API to correlate noise events with weather conditions.</li>
    <li><strong>Traffic Data Collection (<em>Optional</em>):</strong> Integrates with Telraam API to collect traffic data, allowing analysis of noise levels in relation to traffic conditions. <em>Note: A dedicated YOLO-powered traffic counting script is in development and will be available soon.</em></li>
    <li><strong>Image Capture (<em>Optional</em>):</strong> Captures images using an IP camera or Raspberry Pi camera when noise levels exceed a specified threshold.</li>
    <li><strong>Notifications (<em>Optional</em>):</strong> Sends notifications via Discord and Pushover when certain events occur (e.g., high noise levels, API failures).</li>
    <li><strong>Configurable Timezone:</strong> Adjusts timestamps according to the specified timezone offset.</li>
    <li><strong>Error Handling and Logging:</strong> Robust error handling with detailed logging for troubleshooting.</li>
</ul>

<h2>Usages</h2>

<ul>
    <li>Monitor loud traffic, planes, live events, and more.</li>
    <li>Create insightful graphics to share statistics with authorities.</li>
    <li>Analyze environmental noise in correlation with weather and traffic data.</li>
</ul>

<h2>Getting Started</h2>

<h3>Prerequisites</h3>

<p>Before using NoiseBuster, ensure the following prerequisites are met:</p>

<ul>
    <li>Linux-based system (e.g., Ubuntu, Debian, Raspberry Pi OS).</li>
    <li>Python 3.6 or higher installed.</li>
    <li>A USB-connected sound level meter. All models with USB communication capabilities should work. Other types like RS485 models and ESP devices with calibrated microphones could be used, but may require additional setup by the user.</li>
    <li>Internet connection for API integrations (e.g., OpenWeatherMap, Telraam).</li>
    <li><strong>Optional but recommended:</strong> InfluxDB 2.x and Grafana for data storage and visualization.</li>
    <li><strong>Optional:</strong> MQTT broker if you wish to publish data to an MQTT broker.</li>
    <li><strong>Optional:</strong> Docker installed for containerized deployment.</li>
</ul>
<h3>Installation</h3>

<ol>
    <li>Clone the repository using Git:
        <div style="position: relative;">
            <pre>git clone https://github.com/silkyclouds/NoiseBuster.git</pre>
            <button onclick="copyToClipboard('git clone https://github.com/silkyclouds/NoiseBuster.git')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
        </div>
        <p>Navigate to the <code>NoiseBuster</code> directory:</p>
        <div style="position: relative;">
            <pre>cd NoiseBuster</pre>
            <button onclick="copyToClipboard('cd NoiseBuster')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
        </div>
    </li>
    <li>Build the Docker image:
        <div style="position: relative;">
            <pre>docker build -t noisebuster .</pre>
            <button onclick="copyToClipboard('docker build -t noisebuster .')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
        </div>
    </li>
    <li>Run the Docker container:
        <div style="position: relative;">
            <pre>docker run -d --name noisebuster -p 8086:8086 -p 3000:3000 noisebuster</pre>
            <button onclick="copyToClipboard('docker run -d --name noisebuster -p 8086:8086 -p 3000:3000 noisebuster')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
        </div>
        <p>This will start the NoiseBuster container with InfluxDB and Grafana accessible on ports 8086 and 3000, respectively.</p>
    </li>
</ol>

<h3>Hardware Recommendations</h3>

<ul>
    <li><strong>PoE Splitter:</strong> If you want to power your device using PoE, consider using a <a href="https://www.aliexpress.com/item/1005006375194025.html" target="_blank">PoE Splitter</a>.</li>
    <li><strong>IP65 Box:</strong> For outdoor usage of your volume meter, I recommend using an <a href="https://www.aliexpress.com/item/1005005848967422.html" target="_blank">IP65 box</a> to protect the device.</li>
    <li><strong>Volume Meter:</strong> I use this <a href="https://www.aliexpress.com/item/1005006419144001.html" target="_blank">USB volume meter</a>, which runs smoothly on a Raspberry Pi and is powered directly through USB.</li>
    <li><strong>Linux-Compatible Board:</strong> Use a Raspberry Pi or any other board capable of running Linux.</li>
    <li><strong>Virtual Machines and Containers:</strong> You can also run NoiseBuster in a VM, LXC, or other virtual environment, and simply pass through the USB volume meter, avoiding dedicated hardware.</li>
</ul>

<h3>Hardware Requirements</h3>

<ul>
    <li><strong>USB Sound Meter:</strong>
        <ul>
            <li>The application is designed to work with USB-connected sound level meters.</li>
            <li><strong>Example Device:</strong> 
                <a href="https://fr.aliexpress.com/item/1005006973608966.html">USB Sound Level Meter on AliExpress</a>
            </li>
            <li>Ensure the device supports USB communication.</li>
            <li>For devices not automatically detected, you may need to specify the USB vendor ID and product ID in the configuration. Use the <code>lsusb</code> command to find these IDs.</li>
        </ul>
    <p align="center">
      <img src="soundmeter_usb.png" alt="USB Sound Meter Example" width="50%">
      <br>
      <em>Search for this type of USB meter</em>
    </p>
    </li>
    <li><strong>Camera (<em>Optional</em>):</strong>
        <ul>
            <li><strong>IP Camera:</strong> Supports RTSP or HTTP protocols. Provide the camera's URL in the configuration.</li>
            <li><strong>Raspberry Pi Camera:</strong> Connects directly to the Raspberry Pi. Requires the <code>picamera</code> library.</li>
        </ul>
    </li>
</ul>

<h2>Configuration</h2>

<p>All configuration settings are stored in the <code>config.json</code> file. Here is how to set up your configuration:</p>

<ol>
    <li>Open <code>config.json</code> in a text editor. Keep all default IP addresses as <code>localhost</code> or <code>127.0.0.1</code> to ensure it works out of the box.</li>
    <li>Configure each section:</li>
</ol>

<ul>
    <li><strong>InfluxDB Configuration:</strong>
        <ul>
            <li>Set <code>"enabled": true</code> to store data in InfluxDB.</li>
            <li>Provide your InfluxDB <code>host</code>, <code>port</code>, <code>token</code>, <code>org</code>, and <code>bucket</code> names.</li>
            <li>Ensure you create buckets named <code>"noise_buster"</code> and <code>"noise_buster_realtime"</code>.</li>
            <li><strong>API Keys:</strong> Follow the <a href="https://docs.influxdata.com/influxdb/v2.0/get-started/">InfluxDB setup guide</a> to create your organization, buckets, and API tokens.</li>
        </ul>
    </li>
    <li><strong>Pushover Configuration (Optional):</strong>
        <ul>
            <li>Set <code>"enabled": true</code> to receive Pushover notifications.</li>
            <li>Provide your <code>user_key</code> and <code>api_token</code>. Register at <a href="https://pushover.net/">Pushover</a>.</li>
        </ul>
    </li>
    <li><strong>Weather Configuration (Optional):</strong>
        <ul>
            <li>Set <code>"enabled": true</code> to fetch weather data.</li>
            <li>Provide your OpenWeatherMap <code>api_key</code> and <code>location</code>. Sign up at <a href="https://openweathermap.org/api">OpenWeatherMap API</a>.</li>
        </ul>
    </li>
    <li><strong>MQTT Configuration (Optional):</strong>
        <ul>
            <li>Set <code>"enabled": true</code> to publish data to an MQTT broker.</li>
            <li>Provide your MQTT <code>server</code>, <code>port</code>, <code>user</code>, and <code>password</code>. Learn more at <a href="https://mqtt.org/">mqtt.org</a>.</li>
        </ul>
    </li>
    <li><strong>Camera Configuration (Optional):</strong>
        <ul>
            <li>Set <code>"use_ip_camera": true</code> or <code>"use_pi_camera": true</code> based on your setup.</li>
            <li>If using an IP camera, provide the <code>ip_camera_url</code>.</li>
        </ul>
    </li>
    <li><strong>Device and Noise Monitoring Configuration:</strong>
        <ul>
            <li>Specify the <code>device_name</code> for identification.</li>
            <li>Set <code>minimum_noise_level</code> in decibels to trigger events.</li>
            <li>Specify <code>image_save_path</code> where images will be stored.</li>
            <li>If automatic USB detection fails, provide <code>usb_vendor_id</code> and <code>usb_product_id</code>. Use the <code>lsusb</code> command to find these IDs.</li>
        </ul>
    </li>
    <li><strong>Telraam API Configuration (Optional):</strong>
        <ul>
            <li>Set <code>"enabled": true</code> to collect traffic data.</li>
            <li>Provide your Telraam <code>api_key</code> and <code>segment_id</code>. More info at <a href="https://telraam.net/">Telraam</a>.</li>
        </ul>
    </li>
    <li><strong>Timezone Configuration:</strong>
        <ul>
            <li>Set <code>timezone_offset</code> relative to UTC.</li>
        </ul>
    </li>
    <li><strong>Discord Configuration (Optional):</strong>
        <ul>
            <li>Set <code>"enabled": true</code> to send notifications to Discord.</li>
            <li>Provide your Discord <code>webhook_url</code>. Create one at <a href="https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks">Discord Webhooks</a>.</li>
        </ul>
    </li>
</ul>

<ol start="3">
    <li>Save <code>config.json</code>.</li>
</ol>

<h2>Running the Script</h2>

<h3>Using Docker (Recommended)</h3>

<p>The easiest way to get started is by using Docker. A <code>docker-compose.yml</code> file is provided to set up all the necessary components.</p>

<ol>
    <li>Ensure Docker and Docker Compose are installed on your system. Learn more at <a href="https://docs.docker.com/get-docker/">Docker Installation</a>.</li>
    <li>Navigate to the project directory:</li>
    <div style="position: relative;">
        <pre>cd NoiseBuster</pre>
        <button onclick="copyToClipboard('cd NoiseBuster')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
    </div>
    <li>Edit the <code>docker-compose.yml</code> file if necessary.</li>
    <li>Run Docker Compose:</li>
    <div style="position: relative;">
        <pre>docker-compose up -d</pre>
        <button onclick="copyToClipboard('docker-compose up -d')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
    </div>
    <li>Pass the USB device to the Docker container:
        <ol>
            <li>List your USB devices using the <code>lsusb</code> command.</li>
            <li>Identify your USB sound meter in the list.</li>
            <li>Note the Bus and Device IDs (e.g., Bus 003 Device 011).</li>
            <li>Modify the <code>devices</code> section in <code>docker-compose.yml</code> to include your device:</li>
            <div style="position: relative;">
                <pre>
devices:
  - "/dev/bus/usb/003/011:/dev/bus/usb/003/011"
                </pre>
                <button onclick="copyToClipboard('/dev/bus/usb/003/011:/dev/bus/usb/003/011')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
            </div>
        </ol>
    </li>
    <li>Check the logs to ensure it's running correctly:</li>
    <div style="position: relative;">
        <pre>docker-compose logs -f</pre>
        <button onclick="copyToClipboard('docker-compose logs -f')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
    </div>
</ol>

<h3>Using Python Directly</h3>

<ol>
    <li>Ensure the USB sound meter is connected to your computer.</li>
    <li>Activate the virtual environment if you created one:</li>
    <div style="position: relative;">
        <pre>source env/bin/activate</pre>
        <button onclick="copyToClipboard('source env/bin/activate')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
    </div>
    <li>Run the application:</li>
    <div style="position: relative;">
        <pre>python noisebuster.py</pre>
        <button onclick="copyToClipboard('python noisebuster.py')" style="position: absolute; right: 10px; top: 10px;">Copy</button>
    </div>
</ol>

<h2>Hardware Recommendations</h2>

<ul>
    <li><strong>PoE Splitter:</strong> If you want to power your device using PoE, consider using a <a href="https://www.aliexpress.com/item/1005006375194025.html" target="_blank">PoE Splitter</a>.</li>
    <li><strong>IP65 Box:</strong> For outdoor usage of your volume meter, I recommend using an <a href="https://www.aliexpress.com/item/1005005848967422.html" target="_blank">IP65 box</a> to protect the device.</li>
    <li><strong>Volume Meter:</strong> I use this <a href="https://www.aliexpress.com/item/1005006419144001.html" target="_blank">USB volume meter</a>, which runs smoothly on a Raspberry Pi and is powered directly through USB.</li>
    <li><strong>Linux-Compatible Board:</strong> Use a Raspberry Pi or any other board capable of running Linux.</li>
    <li><strong>Virtual Machines and Containers:</strong> You can also run NoiseBuster in a VM, LXC, or other virtual environment, and simply pass through the USB volume meter, avoiding dedicated hardware.</li>
</ul>

<h2>License</h2>

<p>This project is licensed under the GNU GPLv3. This license allows for free usage and modification of the code for non-commercial purposes. For commercial use, explicit permission from the project owner is required. By choosing this option, I aim to encourage open-source collaboration while maintaining control over commercial applications of NoiseBuster. For further details on the license, refer to the <a href="LICENSE">GNU GPLv3 License</a>.</p>

<h2>Contributing</h2>

<ol>
    <li>Fork the repository.</li>
    <li>Create a new branch for your changes.</li>
    <li>Submit a pull request with a detailed explanation of your changes.</li>
</ol>

<p>I'm actively developing a vehicle detection and counting module based on YOLOv11 to correlate noise events with specific vehicle types. If you're interested in helping improve this model or contributing in other ways, please reach out! Any contributions to the detection and accuracy of vehicle classification would be invaluable.</p>

<h2>Next Steps</h2>

<ul>
    <li>Adding vehicle detection using OpenCV to correlate noise events with specific vehicles.</li>
    <li>Providing a centralized InfluxDB instance for users to contribute data.</li>
    <li>Investigating other hardware options like ESP devices for sound monitoring.</li>
    <li>Implementing better data retention policies to manage database size.</li>
    <li>A dedicated YOLO-powered traffic counting script is in development and will be available soon.</li>
</ul>

<h2>Project</h2>

<p>This project was initiated by Raphael Vael. I welcome anyone interested in improving NoiseBuster to join the effort. Whether it's refining the vehicle detection model, optimizing the noise detection algorithms, or expanding functionality, your input is greatly valued!</p>

</body>
</html>
