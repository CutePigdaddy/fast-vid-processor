import ffmpeg
import requests
from static_ffmpeg import add_paths
import os
import re
add_paths()
HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
  "Referer": "https://www.bilibili.com"
}
def fix_audio_duration(input_path):
  """
  基于 ffmpeg 自动修复音频文件在下载后的时长显示问题。
  通过简单的流复制重新封装，可以校正部分 m4a 文件在播放器中时长不准的情况。
  
  :param input_path: 需要修复的音频文件路径（通常为 .m4a 格式）
  :type input_path: str
  :return: None，修复后的文件会以 '_fixed' 为后缀保存在原文件同目录下
  """
  name, ext = os.path.splitext(input_path)
  output_path = f"{name}_fixed.{ext}"
  try:
    (
      ffmpeg
        .input(input_path)
        .output(output_path, c='copy')
        .run(overwrite_output=True, quiet=True)
    )
    print(f"修复完成: {output_path}")
  except ffmpeg.Error as e:
    print(f"ffmpeg 修复失败: {e}")

def get_Bvid(URL):
  """
  从给定的 B 站视频 URL 中解析并提取 Bvid (以 BV 开头的唯一标识符)。
  
  :param URL: 包含 Bvid 的 B 站视频路径
  :type URL: str
  :return: 提取到的 Bvid 字符串
  :rtype: str
  :raise ValueError: 如果 URL 中不包含合法的 Bvid 格式时抛出
  """
  Bvid_match = re.search(r'(BV[a-zA-Z0-9]+)', URL)
  if Bvid_match:
    return Bvid_match.group(1)
  else:
    raise ValueError("URL 不含有效 Bvid")
  
def get_cid(URL):
  """
  通过视频 URL 获取 B 站视频对应的 CID (Content ID)，用于后续 API 请求。
  
  :param URL: B 站视频 URL
  :type URL: str
  :return: 包含视频分 P 信息的字典列表。每个字典包含 'cid', 'part' 等字段
  :rtype: list
  """
  api_url = f"https://api.bilibili.com/x/player/pagelist?bvid={get_Bvid(URL)}"
  response = requests.get(api_url, headers=HEADERS)
  data = response.json()
  if data['code'] == 0:
    print("请求 CID 成功")
    return data['data']
  else:
    print("请求 CID 失败")
    return []
  