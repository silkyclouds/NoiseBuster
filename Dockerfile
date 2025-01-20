# Use a lightweight base image with Python 3.9 from docker.io
FROM docker.io/python:3.9-slim

# (Optionnal)
ENV READTHEDOCS=True
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies, including libusb for PyUSB
RUN apt-get update && \
    apt-get install -y \
        wget \
        gnupg2 \
        curl \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        libusb-1.0-0-dev \
        btop \
        htop \
        nano \
        net-tools \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the main Python script, config file, and dependencies list
COPY noisebuster.py .
COPY config.json .
COPY requirements.txt .

# Upgrade pip (conseillé)
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for storing captured images (if needed)
RUN mkdir -p /images

# Set the command to start the application
CMD ["python", "noisebuster.py"]
