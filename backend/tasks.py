import logging
from celery import Celery
from config import settings
from to_text import process_video_to_text, extract_audio_step, separate_vocal_step, transcribe_vocal_step
from modules.database import db

logger = logging.getLogger(__name__)

app = Celery(
    'tasks',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)


@app.task(bind=True)
def text_task(self, file_hash: str):
    """
    视频全自动处理任务：提取字幕/提取音轨 -> 人声分离 -> 语音转文字。
    入参为文件的 SHA-256 哈希值。
    to_text.py 内部通过 task_instance.update_state() 更新 Redis 中间进度。
    完成后在此处更新 SQLite 状态为 success / failed。
    """
    try:
        logger.info(f"[{file_hash}] 开始处理 text_task")
        result = process_video_to_text(file_hash, task_instance=self)
        # 处理成功 → 更新数据库
        db.update_file_status(file_hash, "success")
        logger.info(f"[{file_hash}] text_task 处理完成")
        return result
    except Exception as e:
        logger.error(f"[{file_hash}] text_task 处理失败: {e}")
        db.update_file_status(file_hash, "failed")
        raise  # 重新抛出让 Celery 标记为 FAILURE


@app.task(bind=True)
def extract_audio_task(self, file_hash: str):
    """
    独立音轨提取任务：仅从视频中提取音轨。
    """
    try:
        output_file = extract_audio_step(file_hash)
        return {"output_file": output_file, "status": "success"}
    except Exception as e:
        logger.error(f"[{file_hash}] extract_audio_task 失败: {e}")
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
        raise


@app.task(bind=True)
def stt_task(self, file_hash: str, vocal_path: str):
    """
    独立语音转文字任务（需要提供人声音频路径）。
    """
    try:
        output_file = transcribe_vocal_step(file_hash, vocal_path)
        return {"output_file": output_file, "status": "success"}
    except Exception as e:
        logger.error(f"[{file_hash}] stt_task 失败: {e}")
        raise