# Utiliser l'image de base Python 3
FROM python:3

# Définir le répertoire de travail dans le conteneur
WORKDIR /usr/src/app

# Installer les outils nécessaires
RUN apt-get update && apt-get install -y usbutils

# Installer virtualenv
RUN pip install virtualenv

# Copier les fichiers de dépendance dans le conteneur
COPY setuptools.txt ./
COPY requirements.txt ./

# Installer les dépendances du setuptools.txt
RUN pip install --no-cache-dir -r setuptools.txt

# Créer un environnement virtuel
RUN virtualenv venv

# Activer l'environnement virtuel
ENV PATH="/usr/src/app/venv/bin:$PATH"

# Installer les dépendances du requirements.txt dans l'environnement virtuel
RUN . venv/bin/activate && pip install --no-cache-dir -r setuptools.txt && pip install --no-cache-dir -r requirements.txt

# Copier le script dans le conteneur
COPY . .

# Exécuter le script à l'intérieur de l'environnement virtuel
CMD . venv/bin/activate && python ./noise_to_influx_wan.py 2>&1
