from celery import Celery
from config import settings
from to_text import process_video_to_text, extract_audio_step, separate_vocal_step, transcribe_vocal_step
from to_photo import process_video_to_photo

app = Celery(
    'tasks',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

@app.task(bind=True)
def text_task(self, input_file):
    """
    视频全自动处理任务：提取字幕/提取音轨 -> 人声分离 -> 语音转文字。
    """
    result = process_video_to_text(input_file, task_instance=self)
    return result

@app.task(bind=True)
def extract_audio_task(self, input_file):
    """
    音轨提取任务：仅从视频中提取音轨。
    """
    task_id = self.request.id
    output_file = extract_audio_step(input_file, task_id)
    return {
        "output_file": output_file,
        "status": "success"
    }

@app.task(bind=True)
def vocal_task(self, input_file):
    """
    人声提取任务（从音频文件开始）。
    """
    task_id = self.request.id
    output_file = separate_vocal_step(input_file, task_id)
    return {
        "output_file": output_file,
        "status": "success"
    }

@app.task(bind=True)
def stt_task(self, input_file):
    """
    语音转文字任务（从音频文件开始）。
    """
    task_id = self.request.id
    output_file = transcribe_vocal_step(input_file, task_id)
    return {
        "output_file": output_file,
        "status": "success"
    }

@app.task(bind=True)
def photo_task(self, input_file):
    """
    视频/图片处理任务（预留）。
    """
    result = process_video_to_photo(input_file, task_instance=self)
    return result