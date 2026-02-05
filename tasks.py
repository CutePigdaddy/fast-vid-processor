from celery import Celery
from modules.track import Separator
from config import settings

app = Celery(
  'tasks',
  broker=settings.CELERY_BROKER_URL,
  backend=settings.CELERY_RESULT_BACKEND
)

@app.task(bind = True)
def extract_audio_task(self,input_file):
  separator=Separator()
  output_file=separator.extract_audio(input_file,settings.DEFAULT_OUTPUT_DIR)
  return {
    "output_file": output_file,
    "status": "success"
  }