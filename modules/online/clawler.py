import requests
import re
import json
import os
from bilibili_stream import BilibiliStream
from utils import fix_audio_duration
AUDIO_PATH = "Audio"
VIDEO_PATH = "Video"
VIDEOSHOT_PATH = "Videoshot"
HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
  "Referer": "https://www.bilibili.com"
}
Session = requests.Session()

def get_playinfo_data(URL) -> dict:
  """
  获取playinfo的data字典
  
  :param URL: B站视频链接
  :return: 返回playinfo字典
  :rtype: dict[str, Any]
  """
  Session.headers.update(HEADERS)
  response = Session.get(URL)
  if response.status_code == 200:
    print("获取网页HTML成功！")
  else:
    raise requests.ConnectionError("连接网页失败")
  html = response.text
  title_match = re.search(r'<title>(.*?)</title>', html)
  title = title_match.group(1) if title_match else f"video_{URL}"
  playinfo_match = re.search(r'window\.__playinfo__=(.*?)</script>', html)
  if not playinfo_match:
    raise ValueError("Could not find playinfo data in the page source.")
  playinfo = json.loads(playinfo_match.group(1))
  playinfo["data"]["title"] = title
  return playinfo["data"]

def download_audio(data,range = '0'):
  """
  下载音频文件, get_playinfo_data(URL)的返回值作为参数传入

  :param data: playinfo的data字典
  :param range: 获取音频的字节段
  """
  baseUrl = data['dash']['audio'][0]['baseUrl']
  filename = f"{data['title']}.m4a"
  filepath = os.path.join(AUDIO_PATH,filename)
  
  if range != '0':
    headers = {
      **HEADERS,
      "Range":f"bytes={range}"
    }
    Session.headers.update(headers)
  response = Session.get(baseUrl,stream=True)
  if response.status_code == 200 or 206:
    print(f"获取|||{filename}|||成功")
  else:
    raise requests.ConnectionError("音频下载失败")
  with open(filepath,'wb') as f:
    for chunk in response.iter_content(1024*1024):
      f.write(chunk)
  if range!='0':
    fix_audio_duration(filepath)

def download_videoshot(URL):
  """
  通过API请求获得视频快照，可用于AI总结
  
  :param URL: 含Bvid的B站视频链接
  """
  
  Bvid_match = re.search(r'(BV[a-zA-z0-9]+)',URL)
  if Bvid_match:
    Bvid = Bvid_match.group(1)
  else:
    raise ValueError("URL不含Bvid")
  
  Session.headers.update(HEADERS)
  response = Session.get(f"https://api.bilibili.com/x/player/videoshot?bvid={Bvid}")
  if response.status_code == 200:
    data = response.json()
    images = data["data"]["image"]
    for i,image_url in enumerate(images,start = 1):
      if image_url.startswith("//"):
        image_url = f"https:{image_url}"
      response = Session.get(image_url)
      if response.status_code == 200:
        dirpath = os.path.join(VIDEOSHOT_PATH,Bvid)
        os.makedirs(dirpath,exist_ok=True)
        filepath = os.path.join(dirpath,f"{Bvid}_{i}.jpg")
        with open(filepath,'wb') as f:
          f.write(response.content)
        print(f"保存{filepath}成功！")
      else:
        raise requests.ConnectionError("缩略图获取失败")
  else:
    raise requests.ConnectionError(f"API 业务报错: {response.json()['message']}")

def download_subtitle(URL):
  """
  下载视频的字幕
  
  :param URL: B站视频的链接
  """
  
#https://www.bilibili.com/video/BV1d1ktBCEaJ/?spm_id_from=333.1007.tianma.1-3-3.click&vd_source=ede24bcc29b6f6c3df591e75217018c8
if __name__ == "__main__":
  
  os.makedirs('Audio',exist_ok=True)
  while True:
    URL = input("URL:")
    download_audio(get_playinfo_data(URL))
  #playinfo_data = get_playinfo_data(URL)
  #baseUrl = playinfo_data["dash"]["audio"][0]["baseUrl"]
  #index_range = playinfo_data["dash"]["audio"][0]["SegmentBase"]["indexRange"]
  #download_audio(playinfo_data,"0-126373")
  #Audio = BilibiliStream(baseUrl,index_range)
  #Audio.load_index()
  #print(Audio.cal_duration(),playinfo_data["dash"]["duration"])
  #audio_segments = Audio.get_segments()
  #print(audio_segments[0],audio_segments[1],audio_segments[2])

