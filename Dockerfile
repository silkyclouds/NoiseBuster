# Use Python 3.10 as the base image to ensure compatibility with dependencies.                        
FROM python:3.10-slim

# Install required system dependencies.
RUN apt-get update && \
    apt-get install -y wget gnupg2 curl software-properties-common apt-transport-https ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Add InfluxDB GPG key and repository.
RUN wget -q https://repos.influxdata.com/influxdata-archive_compat.key && \
    gpg --dearmor -o /usr/share/keyrings/influxdb-archive-keyring.gpg influxdata-archive_compat.key && \
    echo "deb [signed-by=/usr/share/keyrings/influxdb-archive-keyring.gpg] https://repos.influxdata.com/debian stable main" > /etc/apt/sources.list.d/influxdb.list && \
    apt-get update && \
    apt-get install -y influxdb

# Add Grafana GPG key and repository.
RUN wget -q -O - https://packages.grafana.com/gpg.key | gpg --dearmor -o /usr/share/keyrings/grafana-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/grafana-keyring.gpg] https://packages.grafana.com/oss/deb stable main" > /etc/apt/sources.list.d/grafana.list && \
    apt-get update && \
    apt-get install -y grafana

# Set up the working directory.
WORKDIR /app

# Copy the application code and requirements file.
COPY . /app

# Install Python dependencies from requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Expose necessary ports for InfluxDB and Grafana.
EXPOSE 8086 3000

# Set the entrypoint for the Docker container.
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
