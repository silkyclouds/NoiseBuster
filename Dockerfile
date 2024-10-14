# Use the official Python image as the base
FROM python:3.9-slim

# Install necessary system packages
RUN apt-get update && \
    apt-get install -y wget gnupg2 curl software-properties-common apt-transport-https ca-certificates supervisor && \
    rm -rf /var/lib/apt/lists/*

# Install InfluxDB
RUN wget -qO- https://repos.influxdata.com/influxdb.key | apt-key add - && \
    echo "deb https://repos.influxdata.com/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/influxdb.list && \
    apt-get update && \
    apt-get install -y influxdb

# Install Grafana
RUN wget -q -O - https://packages.grafana.com/gpg.key | apt-key add - && \
    add-apt-repository "deb https://packages.grafana.com/oss/deb stable main" && \
    apt-get update && \
    apt-get install -y grafana

# Expose necessary ports
EXPOSE 8086 3000

# Set up working directory
WORKDIR /app

# Copy NoiseBuster code to the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Supervisor configuration file
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create directories for InfluxDB and Grafana data
RUN mkdir -p /var/lib/influxdb2 && \
    mkdir -p /var/lib/grafana && \
    mkdir -p /app/images

# Set environment variables for InfluxDB
ENV INFLUXDB_REPORTING_DISABLED=true
ENV INFLUXDB_HTTP_BIND_ADDRESS=:8086

# Set environment variables for Grafana
ENV GF_SECURITY_ADMIN_USER=admin
ENV GF_SECURITY_ADMIN_PASSWORD=admin

# Set entrypoint to Supervisor
CMD ["/usr/bin/supervisord"]
