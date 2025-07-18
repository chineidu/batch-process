# Celery Tutorials

## Table of Contents

- [Celery Tutorials](#celery-tutorials)
  - [Table of Contents](#table-of-contents)
  - [Different Ways of Invoking Tasks](#different-ways-of-invoking-tasks)

## Different Ways of Invoking Tasks

- Using `.delay()` method: This sends the task to the queue for execution.

```py
my_task.delay(arg1,arg2, kwarg1=kwarg1, kwarg2=kwarg2)
```

- 