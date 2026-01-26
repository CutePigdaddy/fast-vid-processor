import ffmpeg
from static_ffmpeg import add_paths
import os
add_paths()

def fix_audio_duration(input_path):
  """
  基于ffmpeg自动修复音频文件时长
  
  :param input_path: 输入文件路径
  """
  name, ext = os.path.splitext(input_path)
  output_path = f"{name}_fixed.{ext}"
  try:
    (
      ffmpeg
        .input(input_path)
        .output(output_path,c='copy')
        .run(overwrite_output = True,quiet=True)
    )
    print(f"修复完成:{output_path}")
  except ffmpeg.Error as e:
    print(f"ffmpeg 修复失败:{e}")
