import os
import logging
from pathlib import Path
from modules.track import Separator, distractor
from modules.audio import LongAudioProcessor
from config import settings

logger = logging.getLogger(__name__)

def extract_audio_step(input_path: str, task_id: str):
    """模块化步骤：提取音轨到 track 目录"""
    os.makedirs(settings.TRACK_DIR, exist_ok=True)
    separator = Separator()
    # 现在 Separator 不再强制创建子目录，直接提取到 TRACK_DIR
    extracted_audios = separator.extract_audio(input_path, settings.TRACK_DIR)
    
    if not extracted_audios:
        raise Exception("未提取到音轨")
    
    # 为了保持外部调用的统一性（使用 task_id.mp3），我们依然做一次重命名
    raw_audio = extracted_audios[0]
    target_track_path = os.path.join(settings.TRACK_DIR, f"{task_id}.mp3")
    
    if os.path.abspath(raw_audio) != os.path.abspath(target_track_path):
        if os.path.exists(target_track_path):
            os.remove(target_track_path)
        os.rename(raw_audio, target_track_path)
    
    return target_track_path

def separate_vocal_step(track_path: str, task_id: str):
    """模块化步骤：人声分离到 audio 目录"""
    os.makedirs(settings.AUDIO_DIR, exist_ok=True)
    vocal_path_raw = distractor(track_path, output_dir=settings.AUDIO_DIR)
    
    if not vocal_path_raw:
        raise Exception("人声分离失败")
        
    target_vocal_path = os.path.join(settings.AUDIO_DIR, f"{task_id}.mp3")
    if os.path.exists(target_vocal_path):
        os.remove(target_vocal_path)
    os.rename(vocal_path_raw, target_vocal_path)
    
    return target_vocal_path

def transcribe_vocal_step(vocal_path: str, task_id: str):
    """模块化步骤：语音转文字到 text 目录"""
    os.makedirs(settings.TEXT_DIR, exist_ok=True)
    processor = LongAudioProcessor(model_size="medium")
    final_text_path = os.path.join(settings.TEXT_DIR, f"{task_id}.txt")
    
    result = processor.process_long_audio(vocal_path)
    processor.save_transcription_with_timestamps(result, final_text_path)
    
    return final_text_path

def process_video_to_text(input_path: str, task_instance=None):
    """
    处理视频到文字的任务：提取字幕(优先) -> 提取音轨 -> 人声分离 -> 语音转文字。
    
    :param input_path: 输入视频 file 路径。
    :param task_instance: Celery 任务实例，用于更新状态。
    """
    task_id = task_instance.request.id if task_instance and task_instance.request else Path(input_path).stem
    
    # 确保输出目录存在
    for d in [settings.TRACK_DIR, settings.AUDIO_DIR, settings.TEXT_DIR]:
        os.makedirs(d, exist_ok=True)

    separator = Separator()
    final_text_path = os.path.join(settings.TEXT_DIR, f"{task_id}.txt")
    
    # 1. 尝试提取内置字幕
    logger.info(f"正在尝试提取内置字幕: {input_path}")
    # 直接指定输出到 TEXT_DIR
    extracted_subs = separator.extract_subtitles(input_path, settings.TEXT_DIR)
    
    if extracted_subs:
        logger.info("检测到内置字幕，正在导入...")
        # 取第一路字幕并直接存入 TEXT_DIR
        raw_sub = extracted_subs[0]
        if os.path.exists(final_text_path):
            os.remove(final_text_path)
        os.rename(raw_sub, final_text_path)
        
        if task_instance:
            task_instance.update_state(state='converted', meta={'current': 'subtitles extracted'})
            
        # 即使有了字幕，可能用户还是想要音轨，我们模块化调用
        track_path = extract_audio_step(input_path, task_id)
            
        return {
            "track_file": track_path,
            "audio_file": None,
            "text_file": final_text_path,
            "output_file": final_text_path,
            "method": "subtitle_extraction"
        }

    # 2. 如果没有字幕，则走模块化流程
    logger.info("未检测到内置字幕，进入 AI 语音转文字流...")
    
    # 2.1 提取音轨
    track_path = extract_audio_step(input_path, task_id)
    
    if task_instance:
        task_instance.update_state(state='separated', meta={'current': 'audio extracted'})

    # 2.2 人声分离
    logger.info(f"开始人声分离: {track_path}")
    vocal_path = separate_vocal_step(track_path, task_id)
    
    if task_instance:
        task_instance.update_state(state='distracted', meta={'current': 'vocals separated'})

    # 2.3 语音转文字
    logger.info(f"开始语音转文字: {vocal_path}")
    final_text_path = transcribe_vocal_step(vocal_path, task_id)

    if task_instance:
        task_instance.update_state(state='converted', meta={'current': 'text converted'})

    return {
        "track_file": track_path,
        "audio_file": vocal_path,
        "text_file": final_text_path,
        "output_file": final_text_path,
        "method": "ai_stt"
    }
