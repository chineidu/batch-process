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
uvr celery -A path.to.module beat --loglevel=info

# e.g.
uvr celery -A src.celery.app beat --loglevel=info
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

