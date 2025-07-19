# Celery Tutorials

## Table of Contents

- [Celery Tutorials](#celery-tutorials)
  - [Table of Contents](#table-of-contents)
  - [Different Ways of Invoking Tasks](#different-ways-of-invoking-tasks)

## Different Ways of Invoking Tasks

1) Using `.delay()` method: This is the simplest way to invoke a task. It sends the task to the queue for execution and returns an `AsyncResult` object without waiting for the task to complete.

   ```py
   my_task.delay(arg1,arg2, kwarg1=kwarg1, kwarg2=kwarg2)
   ```

2) Using `apply_async()` method: This sends the task to the queue for execution and returns an `AsyncResult` object. It provides more control over task execution.

   ```py
   my_task.apply_async(args=[arg1, arg2], kwargs={'kwarg1': kwarg1}, countdown=10)
   ```

3) Using `send_task()` method: This sends the task to the queue for execution by `name`. Ideal when the sender doesn't have the task code loaded, or when working across services.

   ```py
   from celery import send_task

   send_task('path.to.task', args=[arg1, arg2], kwargs={'kwargs1': 'x'})
   # e.g
   send_task('tasks.add', args=[2, 3], kwargs={'kwargs1': '2', 'kwargs2': '3'})

   ```

4) Using `group` Method: This method allows you to group multiple tasks together and execute them in parallel.

   ```py
   from celery import group

   job = group(task.s(arg1, arg2) for arg1, arg2 in zip(arg_list1, arg_list2))
   result = job.apply_async()
   ```

5) Using `chord` Method: This method allows you to execute a group of tasks in parallel and then execute a callback task once all the tasks in the group have completed.

   ```py
   @app.task
   def add(x, y):
    return x + y

   @app.task
   def sum_tasks(results):
    """Sum"""
    return sum(results)

   # Run the tasks sequentially
   results = [add.s(i, i) for i in range(10)]

   # Run the final result task once all the tasks have completed using `chord`
   job = chord(results, sum_tasks.s())
   result = job.apply_async()
   ```

6) Using `chain` Method: This method allows you to chain multiple tasks together so that they execute sequentially.

   ```py
   from celery import chain

   job = chain(task.s(arg1, arg2) | task.s() | task.s())
   result = job.apply_async()
   Using signature Method: This method allows you to create a signature of a task that can be used to invoke the task later.
   ```

7) Using `signature` Method: This method allows you to create a signature of a task that can be used to invoke the task later.

```py
from celery import signature
sig = signature('tasks.add', args=[arg1, arg2], kwargs={'kwargs1': 'x'})
result = sig.apply_async()
```


