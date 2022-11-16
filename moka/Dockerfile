############################################################
# Dockerfile to build Flask App
# Based on
############################################################

# Set the base image
FROM debian:latest

ENV PYTHONUNBUFFERED True


RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get update && apt-get install -y apache2 \
    libapache2-mod-wsgi-py3 \
    build-essential \
    python3 \
    python3-dev\
    python3-pip \
    vim \
 && apt-get clean \
 && apt-get autoremove \
 && rm -rf /var/lib/apt/lists/*


# Copy over and install the requirements

COPY . .
WORKDIR /app
RUN pip install -r requirements.txt


# Copy over the apache configuration file and enable the site
COPY ./moka.conf /etc/apache2/sites-available/moka.conf
RUN a2ensite moka
RUN a2enmod ssl

#inserire certificati di certbot 
COPY ./cert var/www/aw-landingpager-server/cert

# Copy over the wsgi file
RUN mkdir /var/www/aw-landingpager-server
COPY ./lpager_server.wsgi /var/www/aw-landingpager-server/lpager_server.wsgi
COPY ./main_be.py  /var/www/aw-landingpager-server/main_be.py.py


RUN a2dissite 000-default.conf
RUN a2ensite prova.conf

# LINK apache config to docker logs.
RUN ln -sf /proc/self/fd/1 /var/log/apache2/access.log && \
    ln -sf /proc/self/fd/1 /var/log/apache2/error.log




CMD  /usr/sbin/apache2ctl -D FOREGROUND
