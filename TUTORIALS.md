# Celery Tutorials

## Table of Contents

- [Celery Tutorials](#celery-tutorials)
  - [Table of Contents](#table-of-contents)
  - [Different Ways of Invoking Tasks](#different-ways-of-invoking-tasks)

## Different Ways of Invoking Tasks

1) Using `.delay()` method:
   - This is the simplest way to invoke a task.
   - It sends the task to the queue for execution and returns an `AsyncResult` object without waiting for the task to complete.

   ```py
   my_task.delay(arg1,arg2, kwarg1=kwarg1, kwarg2=kwarg2)
   ```

2) Using `apply_async()` method:
   - This sends the task to the queue for execution and returns an `AsyncResult` object.
   - It provides more control over task execution.

   ```py
   my_task.apply_async(args=[arg1, arg2], kwargs={'kwarg1': kwarg1}, countdown=10)
   ```

3) Using `send_task()` method:

   - This sends the task to the queue for execution by `name`.
   - This is used when the task is not imported in the module.

   ```py
   from celery import send_task

   send_task('path.to.task', args=[arg1, arg2], kwargs={'kwargs1': 'x'})
   # e.g
   send_task('tasks.add', args=[2, 3], kwargs={'kwargs1': '2', 'kwargs2': '3'})

   ```

4) Using `group` Method:
   - This method allows you to group multiple tasks together and execute them in `parallel`.

   ```py
   from celery import group

   job = group(task.s(arg1, arg2) for arg1, arg2 in zip(arg_list1, arg_list2))
   result = job.apply_async()
   ```

5) Using `chord` Method:
   - This method allows you to execute a group of tasks in parallel and then execute a callback task once all the tasks in the group have completed.

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

6) Using `chain` Method:
   - This method allows you to chain multiple tasks together so that they execute `sequentially`.
   - You canchain using `,` or `|`.

   ```py
   from celery import chain

   # Using `|` notation
   job = chain(task.s(arg1, arg2) | task.s() | task.s())
   result = job.apply_async()
   ```

   - If you want to chain tasks without passing inputs, use the `task.si()` method.
   - This ensures the tasks run sequentially without depending on the output of the previous task.

   ```py
   # Using `,` notation
   job = chain(save_user_payment_task.si(), notify_user_task.si(), user_order_task.si())
   ```
