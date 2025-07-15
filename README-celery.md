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
