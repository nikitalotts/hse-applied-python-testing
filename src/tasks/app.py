from celery import Celery
from src.config import Settings

app = Celery('tasks', broker=Settings().MESSAGE_BROKER_URL)
app.autodiscover_tasks(['src.tasks'])
