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

def get_Bvid(URL):
  """
  通过URL获得B站Bvid
  
  :param URL: B站视频URL
  """
  Bvid_match = re.search(r'(BV[a-zA-z0-9]+)',URL)
  if Bvid_match:
    return Bvid_match.group(1)
  else:
    raise ValueError("URL不含Bvid")
  
def get_cid(URL):
  """
  通过URL获得B站cid，返回一个列表，列表每一项是字典，字典里面['cid']就是cid
  
  :param URL: B站视频URL
  """

  api_url = f"https://api.bilibili.com/x/player/pagelist?bvid={get_Bvid(URL)}"
  response = requests.get(api_url,headers=HEADERS)
  data = response.json()
  if data['code'] == 0:
    print("请求cid成功")
    return data['data']
  else:
    print("请求cid失败")
    return []
  