import logging
import os
from celery import Celery
from config import settings
from to_text import process_video_to_text, extract_audio_step, separate_vocal_step, transcribe_vocal_step
from .modules.database import db
from .modules.vision import extract_frames

logger = logging.getLogger(__name__)

app = Celery(
    'tasks',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)


@app.task(bind=True)
def ai_summarize_task(self, file_hash: str):
    """
    独立AI摘要任务（需要提供转写文本路径）。
    """

@app.task(bind=True)
def extract_audio_task(self, file_hash: str):
    """
    独立音轨提取任务：仅从视频中提取音轨。
    """
    try:
        output_file = extract_audio_step(file_hash)
        #数据库更新
        return file_hash
    except Exception as e:
        logger.error(f"[{file_hash}] extract_audio_task 失败: {e}")
        #数据库更新
        raise


@app.task(bind=True)
def vocal_task(self, file_hash: str, track_path: str):
    """
    独立人声分离任务（需要提供已提取的音轨路径）。
    """
    try:
        output_file = separate_vocal_step(file_hash, track_path)
        return {"output_file": output_file, "status": "success"}
    except Exception as e:
        logger.error(f"[{file_hash}] vocal_task 失败: {e}")
        #数据库更新
        raise


@app.task(bind=True)
def asr_task(self, file_hash: str):
    """
    独立语音转文字任务（需要提供人声音频路径）。
    """
    try:
        output_file = transcribe_vocal_step(file_hash)
        return {"output_file": output_file, "status": "success"}
    except Exception as e:
        logger.error(f"[{file_hash}] stt_task 失败: {e}")
        #数据库更新
        raise

@app.task(bind=True)
def extract_keyframes_task(self, file_hash: str):
    """
    独立关键帧提取任务。
    """
    input_file = os.path.join(settings.get_source_dir(settings.DATA_DIR, file_hash), f"{file_hash}.mp4")
    output_dir = settings.get_keyframes_dir(settings.DATA_DIR, file_hash)
    extract_frames(input_file, output_dir)
    #数据库更新
    return {"output_dir": output_dir, "status": "success"}