import logging
import os
from celery import Celery
from config import settings
from to_text import process_video_to_text, extract_audio_step, separate_vocal_step, transcribe_vocal_step
from utils import zip_keyframes
from modules.database import db
from modules.vision import extract_frames
from modules.ai_support import summarize_by_hash

logger = logging.getLogger(__name__)

app = Celery(
    'tasks',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)


@app.task(bind=True)
def ai_summarize_task(self, file_hash: str, task_id: str = None):
    """
    独立AI摘要任务（需要提供转写文本路径）。

    :param file_hash: 文件的唯一标识（MD5 哈希值）。
    :param task_id: 可选的 Celery 任务 ID，用于数据库记录。
    """
    db.update_processed_operation(file_hash, "ai_summarize", "running",task_id=task_id)
    db.update_task_started(task_id)
    result_file = summarize_by_hash(file_hash)['output_file']
    if not result_file:
        logger.error(f"[{file_hash}] ai_summarize_task 失败: 未生成摘要文件")
        db.update_processed_operation(file_hash, "ai_summarize", "failed", task_id=task_id)
        db.update_task_completed(task_id, "failed", error_message="AI摘要失败: 未生成摘要文件")
        raise Exception("AI摘要失败: 未生成摘要文件")
    db.update_processed_operation(file_hash, "ai_summarize", "success", result_path=result_file,task_id=task_id)
    db.update_task_completed(task_id, "success",result_path=result_file)

@app.task(bind=True)
def extract_audio_task(self, file_hash: str, task_id: str = None):
    """
    独立音轨提取任务：仅从视频中提取音轨。
    """
    db.update_processed_operation(file_hash, "extract_audio", "running", task_id=task_id)
    db.update_task_started(task_id)
    try:
        output_file = extract_audio_step(file_hash)
        db.update_processed_operation(file_hash, "extract_audio", "success", result_path=output_file, task_id=task_id)
        db.update_task_completed(task_id, "success",result_path=output_file)
        #数据库更新
        return {"file_hash": file_hash, "status": "success"}
    except Exception as e:
        logger.error(f"[{file_hash}] extract_audio_task 失败: {e}")
        db.update_processed_operation(file_hash, "extract_audio", "failed", task_id=task_id)
        db.update_task_completed(task_id, "failed", error_message=str(e))
        raise


@app.task(bind=True)
def vocal_task(self, file_hash: str, task_id: str = None):
    """
    独立人声分离任务（需要提供已提取的音轨路径）。
    """
    db.update_processed_operation(file_hash, "vocal", "running", task_id=task_id)
    db.update_task_started(task_id)
    try:
        track_path = os.path.join(settings.get_track_dir(settings.DATA_DIR, file_hash), f"{file_hash}.mp3")
        output_file = separate_vocal_step(file_hash, track_path)
        db.update_processed_operation(file_hash, "vocal", "success", result_path=output_file, task_id=task_id)
        db.update_task_completed(task_id, "success",result_path=output_file)
        return {"output_file": output_file, "status": "success"}
    except Exception as e:
        logger.error(f"[{file_hash}] vocal_task 失败: {e}")
        db.update_processed_operation(file_hash, "vocal", "failed", task_id=task_id)
        db.update_task_completed(task_id, "failed", error_message=str(e))
        raise


@app.task(bind=True)
def asr_task(self, file_hash: str, task_id: str = None):
    """
    独立语音转文字任务（需要提供人声音频路径）。
    """
    db.update_processed_operation(file_hash, "transcribe", "running", task_id=task_id)
    db.update_task_started(task_id)
    try:
        output_file = transcribe_vocal_step(file_hash)
        db.update_processed_operation(file_hash, "transcribe", "success", result_path=output_file, task_id=task_id)
        db.update_task_completed(task_id, "success",result_path=output_file)
        return {"output_file": output_file, "status": "success"}
    except Exception as e:
        logger.error(f"[{file_hash}] stt_task 失败: {e}")
        db.update_processed_operation(file_hash, "transcribe", "failed", task_id=task_id)
        db.update_task_completed(task_id, "failed", error_message=str(e))
        raise

@app.task(bind=True)
def extract_keyframes_task(self, file_hash: str, task_id: str = None):
    """
    独立关键帧提取任务。
    """
    db.update_processed_operation(file_hash, "extract_keyframes", "running", task_id=task_id)
    db.update_task_started(task_id)
    input_file = os.path.join(settings.get_source_dir(settings.DATA_DIR, file_hash), f"{file_hash}.mp4")
    try:
        output_dir = settings.get_keyframes_dir(settings.DATA_DIR, file_hash)
        extract_frames(input_file, output_dir)
        zip_path = zip_keyframes(output_dir, file_hash)
        db.update_processed_operation(file_hash, "extract_keyframes", "success", result_path=zip_path, task_id=task_id)
        db.update_task_completed(task_id, "success",result_path=zip_path)
        return {"output_dir": output_dir, "zip_path": zip_path, "status": "success"}
    except Exception as e:
        logger.error(f"[{file_hash}] extract_keyframes_task 失败: {e}")
        db.update_processed_operation(file_hash, "extract_keyframes", "failed", task_id=task_id)
        db.update_task_completed(task_id, "failed", error_message=str(e))
        raise