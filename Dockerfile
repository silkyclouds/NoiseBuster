#Use the base Python 3 image
FROM python:3

#Set the working directory inside the container
WORKDIR /usr/src/app

#Install necessary tools
RUN apt-get update && apt-get install -y usbutils

#Install virtualenv
RUN pip install virtualenv

#Copy dependency files into the container
COPY setuptools.txt ./
COPY requirements.txt ./

#Install dependencies from setuptools.txt
RUN pip install --no-cache-dir -r setuptools.txt

#Create a virtual environment
RUN virtualenv venv

#Activate the virtual environment
ENV PATH="/usr/src/app/venv/bin:$PATH"

#Install dependencies from requirements.txt into the virtual environment
RUN . venv/bin/activate && pip install --no-cache-dir -r setuptools.txt && pip install --no-cache-dir -r requirements.txt

#Copy the script into the container
COPY . .

#Run the script inside the virtual environment
CMD . venv/bin/activate && python ./noise_buster.py 2>&1
