import os
import glob
import logging
from pathlib import Path
from modules.track import Separator, distractor
from modules.audio import LongAudioProcessor
from config import settings

logger = logging.getLogger(__name__)


def _find_source_file(file_hash: str) -> str:
    """在 source 目录中查找源文件（支持任意扩展名）"""
    source_dir = settings.get_source_dir(settings.DATA_DIR, file_hash)
    files = glob.glob(os.path.join(source_dir, f"{file_hash}.*"))
    if not files:
        raise FileNotFoundError(f"未找到源文件: {source_dir}/{file_hash}.*")
    return files[0]


def extract_audio_step(file_hash: str):
    """模块化步骤：提取音轨到 data/<HASH>/track/"""
    input_path = _find_source_file(file_hash)
    track_dir = settings.get_track_dir(settings.DATA_DIR, file_hash)
    os.makedirs(track_dir, exist_ok=True)
    
    separator = Separator()
    extracted_audios = separator.extract_audio(input_path, track_dir)
    
    if not extracted_audios:
        raise Exception("未提取到音轨")
    
    # 重命名为 <HASH>.mp3
    raw_audio = extracted_audios[0]
    target_track_path = os.path.join(track_dir, f"{file_hash}.mp3")
    
    if os.path.abspath(raw_audio) != os.path.abspath(target_track_path):
        if os.path.exists(target_track_path):
            os.remove(target_track_path)
        os.rename(raw_audio, target_track_path)
    
    return target_track_path


def separate_vocal_step(file_hash: str, track_path: str):
    """模块化步骤：人声分离到 data/<HASH>/vocal/"""
    vocal_dir = settings.get_vocal_dir(settings.DATA_DIR, file_hash)
    os.makedirs(vocal_dir, exist_ok=True)
    
    vocal_path_raw = distractor(track_path, output_dir=vocal_dir)
    
    if not vocal_path_raw:
        raise Exception("人声分离失败")
    
    target_vocal_path = os.path.join(vocal_dir, f"{file_hash}.mp3")
    if os.path.exists(target_vocal_path):
        os.remove(target_vocal_path)
    os.rename(vocal_path_raw, target_vocal_path)
    
    return target_vocal_path


def transcribe_vocal_step(file_hash: str, vocal_path: str):
    """模块化步骤：语音转文字到 data/<HASH>/text/"""
    text_dir = settings.get_text_dir(settings.DATA_DIR, file_hash)
    os.makedirs(text_dir, exist_ok=True)
    
    processor = LongAudioProcessor(model_size="medium")
    final_text_path = os.path.join(text_dir, f"{file_hash}.txt")
    
    result = processor.process_long_audio(vocal_path)
    processor.save_transcription_with_timestamps(result, final_text_path)
    
    return final_text_path


def process_video_to_text(file_hash: str, task_instance=None):
    """
    处理视频到文字的完整流水线：
      1. 尝试提取内置字幕（优先）
      2. 提取音轨 -> 人声分离 -> 语音转文字
    
    :param file_hash: 文件的 SHA-256 哈希值
    :param task_instance: Celery 任务实例，用于更新中间状态
    """
    input_path = _find_source_file(file_hash)
    text_dir = settings.get_text_dir(settings.DATA_DIR, file_hash)
    os.makedirs(text_dir, exist_ok=True)

    separator = Separator()
    final_text_path = os.path.join(text_dir, f"{file_hash}.txt")
    
    # 1. 尝试提取内置字幕
    logger.info(f"正在尝试提取内置字幕: {input_path}")
    extracted_subs = separator.extract_subtitles(input_path, text_dir)
    
    if extracted_subs:
        logger.info("检测到内置字幕，正在导入...")
        raw_sub = extracted_subs[0]
        if os.path.exists(final_text_path):
            os.remove(final_text_path)
        os.rename(raw_sub, final_text_path)
        
        if task_instance:
            task_instance.update_state(state='converted', meta={'current': 'subtitles extracted'})
        
        # 即使有了字幕，也提取音轨
        track_path = extract_audio_step(file_hash)
            
        return {
            "track_file": track_path,
            "audio_file": None,
            "text_file": final_text_path,
            "output_file": final_text_path,
            "method": "subtitle_extraction"
        }

    # 2. 如果没有字幕，则走 AI 语音转文字流程
    logger.info("未检测到内置字幕，进入 AI 语音转文字流...")
    
    # 2.1 提取音轨
    track_path = extract_audio_step(file_hash)
    if task_instance:
        task_instance.update_state(state='separated', meta={'current': 'audio extracted'})

    # 2.2 人声分离
    logger.info(f"开始人声分离: {track_path}")
    vocal_path = separate_vocal_step(file_hash, track_path)
    if task_instance:
        task_instance.update_state(state='distracted', meta={'current': 'vocals separated'})

    # 2.3 语音转文字
    logger.info(f"开始语音转文字: {vocal_path}")
    final_text_path = transcribe_vocal_step(file_hash, vocal_path)
    if task_instance:
        task_instance.update_state(state='converted', meta={'current': 'text converted'})

    return {
        "track_file": track_path,
        "audio_file": vocal_path,
        "text_file": final_text_path,
        "output_file": final_text_path,
        "method": "ai_stt"
    }
