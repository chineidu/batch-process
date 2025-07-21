<!-- markdownlint-disable MD033 -->
# Batch-Process With Celery

## Table of Contents

- [Batch-Process With Celery](#batch-process-with-celery)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Celery](#celery)
    - [Configuration](#configuration)
    - [Start Docker Compose](#start-docker-compose)
    - [Start The Worker](#start-the-worker)
    - [Start The Beat Scheduler](#start-the-beat-scheduler)
      - [Beat Scheduler](#beat-scheduler)
    - [Start The Producer](#start-the-producer)
    - [Monitor Tasks](#monitor-tasks)
      - [Built-in Task State Tracker](#built-in-task-state-tracker)
  - [Putting It All Together](#putting-it-all-together)
  - [Deploy Locally (Docker Compose)](#deploy-locally-docker-compose)
    - [Build Images](#build-images)
    - [Run Services](#run-services)
    - [Configure Docker Compose](#configure-docker-compose)
  - [Architecture and Features](#architecture-and-features)
    - [Architecture Overview](#architecture-overview)
  - [Key Features](#key-features)

## Introduction

- This repository contains scripts for simulating the following:

  - Worker processes using `RabbitMQ` for processing long-running tasks in batches.
    - The producer sends a message to the queue.
    - The worker processes the message in an asynchronous manner and stores the result in a database.

  - The application is deployed locally using:
    - Docker Compose
    - Kubernetes (Minikube)

## Celery

### Configuration

- Add task routing and queues to `config/config.yaml`
- Syntax:
  - `path.to.module.*: { queue: queue_name }`

```yaml
# Example (config/config.yaml)
# Task routing and queues
task_routes:
  src.celery.tasks.email_tasks.*: { queue: email }
  src.celery.tasks.data_processing.*: { queue: data }
  src.celery.tasks.periodic_tasks.*: { queue: periodic }
```

### Start Docker Compose

```sh
# Start Docker Compose
docker compose -f docker-compose-dev.yml up

# Stop Docker Compose
docker compose -f docker-compose-dev.yml down
```

### Start The Worker

```sh
uv run worker.py

# OR 
uv run --active worker.py
```

### Start The Beat Scheduler

```sh
uv run celery -A path.to.module beat --loglevel=info

# e.g.
uv run celery -A src.celery.app beat --loglevel=info
```

#### Beat Scheduler

- **Purpose**: Celery Beat is a scheduler designed for periodic tasks within the Celery framework.

- **Mechanism**: It periodically checks a list of predefined tasks.

- **Task Handling**: At their scheduled time, Celery Beat adds these tasks to a message broker (e.g., RabbitMQ, Redis).

- **Execution**: Celery workers then pick up and execute these tasks.

- **Role**: Essentially, Celery Beat acts as a clock that automatically triggers recurring background jobs such as:

  - Sending daily emails
  - Generating reports
  - Cleaning up logs

### Start The Producer

```sh
uv run main_logic.py
```

### Monitor Tasks

- Monitor the tasks using [flower](https://flower.readthedocs.io/en/latest/)

```sh
uv run celery -A src.celery.app flower

# With authentication
export CELERY_FLOWER_USER=admin
export CELERY_FLOWER_PASSWORD=password
uv run celery -A src.celery.app flower --port:5555 --basic_auth=$CELERY_FLOWER_USER:$CELERY_FLOWER_PASSWORD
```

#### Built-in Task State Tracker

```py
from celery.result import AsyncResult

# Get task result object
result = AsyncResult(task_id)

# Check status
print(result.status)  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
print(result.info)    # Additional info about the task
print(result.ready()) # True if task has finished
```

## Putting It All Together

```sh
# Stop Docker Compose (if running)
docker compose -f docker-compose-dev.yml down

# Start Docker Compose
docker compose -f docker-compose-dev.yml up

# Start The Worker
uv run worker.py

# Start The Beat Scheduler
uv run celery -A src.celery.app beat --loglevel=info

# Start Flower (Task Monitoring)
uv run celery -A src.celery.app flower

# Start The Producer/Tasks
uv run main_logic.py
```

## Deploy Locally (Docker Compose)

### Build Images

```sh
# Task Worker
docker buildx build -t celery-worker:v1 -f Dockerfile .
```

### Run Services

```sh
# Start all services
docker-compose up

# Build and start all services
docker-compose up --build

# Start all services in the background
docker-compose up -d

#  Start a specific service
docker-compose up -d worker

# Stop a specific service
docker-compose stop worker

# Start with N replicas
# NOTE: The container name of the service must be unique and determined by Docker automatically.
docker-compose up -d --scale worker=N

# Stop all services
docker-compose down
```

### Configure Docker Compose

- Configure watch in your Docker compose file to mount the project directory without syncing the project virtual environment and to rebuild the image when the configuration changes

```yaml
services:
  local-rabbitmq: # 1st service
    ...

  worker: # 2nd service
    ...
    # Create a `watch` configuration to update the app
      watch:
        - action: sync
          path: ./
          target: /app
          # Folders and files to ignore
          ignore:
            - .venv
            - "**/**/*.ipynb"
            - "my_test.py"
        # Rebuild image if any of these files change
        - action: rebuild
          path: ./pyproject.toml
    ...
```

- Then, run `docker compose watch` to run the container with the development setup.

```sh
docker compose watch
```

- In essence, docker compose watch provides a live development environment where:
  - the project code is automatically kept in sync between the host machine and the running container, excluding the virtual environment.
  - The Docker image for the worker service is automatically rebuilt whenever the project's configuration file (`pyproject.toml`) is modified.

## Architecture and Features

This repository outlines a system designed for batch processing, likely involving machine learning model predictions and data handling. The architecture is composed of several key components:

### Architecture Overview

The system follows a microservices-like pattern, leveraging a message queue for asynchronous task processing. The main components are:

1. **API Service:**
    - Built with FastAPI, it exposes endpoints for initiating tasks (e.g., predictions) and checking service health.
    - Likely responsible for receiving requests and queuing them for background processing.

2. **Message Queue (RabbitMQ):**
    - Used as a broker to decouple the API service from the worker processes.
    - Tasks are published to queues and consumed by workers.

3. **Celery Workers:**
    - Background workers that consume tasks from the message queue.
    - Responsible for executing computationally intensive operations such as:
        - Machine Learning Model Predictions (`ml_prediction_tasks.py`)
        - Data Processing (`data_processing.py`)
        - Email Notifications (`email_tasks.py`)
        - Periodic tasks (`periodic_tasks.py`)

4. **Machine Learning Module:**
    - Contains logic for training ML models (`ml/train.py`) and utility functions (`ml/utils.py`).
    - Pre-trained models (`models/model.pkl`) are likely loaded by workers for predictions.

5. **Data Storage:**
    - The `data/` directory contains various datasets in formats like `.parquet` and `.json`, used for training, testing, and processing.

6. **Configuration Management:**
    - Uses YAML (`src/config/config.yaml`) and Python settings files (`src/config/settings.py`) for managing application configurations.

7. **Database:**
    - Includes database models (`src/database/db_models.py`), suggesting persistence for results or metadata.

8. **Containerization & Deployment:**
    - `Dockerfile` and `docker-compose-dev.yml` indicate containerization for development and potentially deployment.
    - The `rmq-app/` directory with Helm charts suggests deployment orchestration, likely for RabbitMQ and potentially the worker/API services.

<img src="static-files/architecture.png" alt="Architecture Diagram" width="500" height="400"/>

## Key Features

- **Asynchronous Task Processing:** Leverages `Celery` and `RabbitMQ` for efficient handling of long-running tasks.
- **Machine Learning Integration:** Supports ML model training and prediction pipelines.
- **Data Management:** Handles various data formats for processing and analysis.
- **API Endpoints:** Provides a RESTful API for task initiation and monitoring.
- **Containerized Deployment:** Facilitates easy deployment and scaling using Docker and Helm.
- **Configuration Flexibility:** Allows for easy configuration through YAML and Python files.
