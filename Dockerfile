# Use the official Python image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the necessary files into the container
COPY noisebuster.py .
COPY config.json .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create the directory to store images if necessary
RUN mkdir -p /images

# Set the default command
CMD ["python", "noisebuster.py"]
