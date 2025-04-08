# Batch-Process

## Table of Contents

- [Batch-Process](#batch-process)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Code Linting and Formatting](#code-linting-and-formatting)
    - [Linting](#linting)
    - [Type Checking](#type-checking)
    - [Lint and Type Check](#lint-and-type-check)
      - [Locally](#locally)
      - [CICD](#cicd)

## Introduction

- This repository contains scripts for simulating the following:

  - Worker processes using `RabbitMQ` for processing long-running tasks in batches.
    - The producer sends a message to the queue.
    - The worker processes the message in an asynchronous manner and stores the result in a database.

  - The application is deployed locally using:
    - Docker Compose
    - Kubernetes (Minikube)

## Code Linting and Formatting

- The code is linted and formatted using the following tools:
  - Ruff
  - MyPy (Type Checking)
- The Makefile can be found [here](makefile).

### Linting

- This will lint the code and fix any issues.

```sh
make lint-fix
```

### Type Checking

- This will type check the code.

```sh
make type-check
```

### Lint and Type Check

#### Locally

- This will lint and type check the code.

```sh
make format-fix

# OR
make all
```

#### CICD

- This will lint and type check the code without fixing any issues.

```sh
make ci-check
```
