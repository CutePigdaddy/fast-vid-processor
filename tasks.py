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
  """
  Celery 任务：提取视频中的音频轨道。
  使用方法:  extract_audio_task.delay(input_file)
  .delay() 方法会异步执行任务并返回一个 AsyncResult 实例。
  
  :param self: 任务实例本身。
  :param input_file: 输入视频文件路径。
  :return: 包含输出任务UID和文件路径及状态的字典。
  """
  separator=Separator()
  output_file=separator.extract_audio(input_file,settings.DEFAULT_OUTPUT_DIR)
  return {
    "output_file": output_file,
    "status": "success"
  }