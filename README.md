# Interpol-Crawler

# Interpol Crawler Project (Dockerized)

This project scrapes data from Interpol's Red Notices, sends this data to RabbitMQ, and saves it to a Django-based system's database. The project is configured to run within Docker containers.

## Technologies
- **Python**: For web scraping, RabbitMQ connection, and database operations.
- **Selenium & BeautifulSoup**: For web scraping.
- **RabbitMQ**: For data transmission.
- **Django**: For database management and serving data via the web.
- **Docker**: For containerizing the project.
- **pika**: For RabbitMQ connection.

## Project Structure

- **`interpol_scraper.py`**: The Python script that scrapes Interpol data and sends it to RabbitMQ.
- **`consumer.py`**: A script that consumes data from RabbitMQ and saves it to the Django database.
- **`Interpol_Server`**: The Django app with models and database operations.
- **`Dockerfile`**: The configuration file for containerizing the project.
- **`docker-compose.yml`**: The configuration file for running multiple containers (Django, RabbitMQ, Selenium).
- **`requirements.txt`**: The list of required Python libraries.

## Setup

### 1. Install Docker and Docker Compose

To run the Dockerized version of the project, you need to have **Docker** and **Docker Compose** installed.

[Download Docker](https://www.docker.com/products/docker-desktop)  
[Download Docker Compose](https://docs.docker.com/compose/install/)

### 2. Install Dependencies

Python dependencies will be automatically installed within the Docker container as part of the build process. However, to build the Docker image, run the following command in the project directory.

### 3. Start Docker Containers

To start all the required containers for the project, use Docker Compose:

```bash
docker-compose up --build

To start scrabbing from website: 

```bash
docker start interpol_scrapper.py 

To start consuming from rabbiMQ:

First,

```bash
docker-exec -it interpol_server/bin/bash

Then, start the consumer script:

```bash 
python manage.py consumer

