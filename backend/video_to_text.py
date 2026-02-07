import os
import logging
from pathlib import Path
from modules.track import Separator, compresser, distractor
from modules.audio import LongAudioProcessor
from modules.online import get_playinfo_data,download_audio
#配置日志
logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def batch_offline_videos(source_dir: str, output_root: str):
  """
  批量处理离线视频，执行音轨提取、人声分离、压缩以及语音转文字转录。
  
  :param source_dir: 包含视频文件的输入目录路径。
  :type source_dir: str
  :param output_root: 保存转录结果和中间文件的根目录路径。
  :type output_root: str
  """
  #---初始化组件---
  logger.info("正在初始化组件...")
  separator = Separator()
  
  video_extensions = {".mp4", ".avi"}
  source_path = Path(source_dir)
  output_path = Path(output_root)

  #---检索所有目录文件---
  logger.info("正在扫描目录文件")
  video_files = [p for p in source_path.rglob('*') if p.suffix.lower() in video_extensions]
  total = len(video_files)
  logger.info(f"共找到{total}个视频")

  for i,vid in enumerate(video_files, 1):
    rel_path = vid.parent.relative_to(source_path).with_suffix('')
    current_dir = output_path / rel_path
    current_dir.mkdir(parents=True, exist_ok=True)
    final_text_file = current_dir / f"{vid.stem}_transcribed.txt"

    #跳过已经转过的
    if final_text_file.exists():
      logger.info(f"[{i/total}] 跳过已完成的任务:{vid}")
      continue

    logger.info(f"[{i}/{total}]正在处理任务:{vid}")
    try:
      #1.提取音频
      extracted_audio = separator.extract_audio(str(vid),str(current_dir))
      if not extracted_audio:
        logger.warning(f"未能从{vid}获取音频")
        continue

      #默认第一个音轨
      raw_audio_path = Path(extracted_audio[0])
      vocal_audio, compressed_audio = process_audio(raw_audio_path,current_dir)
      temp_files = [raw_audio_path,compressed_audio,vocal_audio]
      for file in temp_files:
        if os.path.exists(file):
          os.remove(file)
    except Exception as e:
      logger.error(f"处理{vid}时发生错误:{e}")
      continue

def batch_online_videos(URL: str, output_root: str = "Audio"):
  """
  下载并处理在线视频音频，执行人声分离、压缩以及语音转文字转录。
  
  :param URL: 视频链接地址。
  :type URL: str
  :param output_root: 输出音频和文本文件的根目录，默认为 "Audio"。
  :type output_root: str
  """
  #---初始化组件---
  logger.info("正在初始化组件...")

  #---下载音频---
  raw_audio = Path(download_audio(get_playinfo_data(URL)))
  working_dir = raw_audio.parent

  logger.info(f"正在处理任务:{raw_audio}")
  vocal_audio, compressed_audio = process_audio(raw_audio,working_dir)
  #temp_files = [raw_audio,compressed_audio,vocal_audio]
  #for file in temp_files:
  #  if os.path.exists(file):
  #    os.remove(file)


def process_audio(raw_audio: Path,working_dir: Path):
  """
  处理单个音频文件：提取人声、压缩音频并转录为带时间轴的文字。
  
  :param raw_audio: 原始音频文件的路径。
  :type raw_audio: Path
  :param working_dir: 存放处理过程中产生的临时文件和最终结果的目录。
  :type working_dir: Path
  :return: 包含 (分离后的人声音频路径, 压缩后的音频路径) 的元组。
  :rtype: tuple[str, str]
  """
  final_text_file = working_dir / f"{raw_audio.stem}_transcribed.txt"
  processer = LongAudioProcessor(model_size="medium")
  #1.提取人声(纯纯bug)
  logger.info(f"正在提取音频人声: {raw_audio}")
  vocal_audio = distractor(str(raw_audio),str(working_dir))
  if not vocal_audio:
    logger.warning(f"人声提取失败:{raw_audio}")
    vocal_audio = str(raw_audio)

  #2.压缩音频
  logger.info(f"正在压缩音频")
  compressed_audio = compresser(str(vocal_audio))

  if not compressed_audio:
    logger.warning(f"未能成功处理音频{vocal_audio}")
    compressed_audio = str(raw_audio)
  #3.音频转文字
  result=processer.process_long_audio(str(compressed_audio))
  processer.save_transcription_with_timestamps(result,str(final_text_file))
  logger.info(f"任务完成！结果保存在:{final_text_file}")

  return vocal_audio,compressed_audio


if __name__ == "__main__":
  E_DRIVE_PATH = ""
  RESULT_OUTPUT = "result_text"

  batch_online_videos("https://www.bilibili.com/video/BV1L5kFBwERZ/?spm_id_from=333.1007.tianma.1-3-3.click&vd_source=ede24bcc29b6f6c3df591e75217018c8")

