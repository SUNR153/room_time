from celery import shared_task
import time

@shared_task
def long_task():
    print("Запуск долгой задачи...")
    time.sleep(5)
    print("✅ Задача завершена")
    return True