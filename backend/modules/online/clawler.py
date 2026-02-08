import requests
import re
import json
import os
from .bilibili_stream import BilibiliStream
from .utils import fix_audio_duration,get_Bvid,get_cid
from .auth import BilibiliLoginManager
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
  爬取视频页面并从中提取 window.__playinfo__ 中的 JSON 数据。
  该数据包含视频和音频的所有流链接 (baseUrl) 以及索引信息。
  
  :param URL: B 站视频播放页面的完整链接
  :type URL: str
  :return: 包含 'dash', 'title' 等核心流信息的 data 字典
  :rtype: dict
  :raise requests.ConnectionError: 网页请求失败时抛出
  :raise ValueError: 源码中未找到 playinfo 数据时抛出
  """
  Session.headers.update(HEADERS)
  response = Session.get(URL)
  if response.status_code == 200:
    print("网页 HTML 获取成功。")
  else:
    raise requests.ConnectionError(f"请求网页失败，状态码: {response.status_code}")
  
  html = response.text
  # 提取视频标题
  title_match = re.search(r'<title>(.*?)</title>', html)
  title = title_match.group(1) if title_match else f"video_{URL}"
  # 处理标题中的非法字符，防止保存文件出错
  title = re.sub(r'[\\/:*?"<>|]', '_', title).replace('_哔哩哔哩_bilibili', '')

  # 提取 playinfo 数据
  playinfo_match = re.search(r'window\.__playinfo__=(.*?)</script>', html)
  if not playinfo_match:
    raise ValueError("无法在源码中解析到 window.__playinfo__ 数据。")
  
  playinfo = json.loads(playinfo_match.group(1))
  playinfo["data"]["title"] = title
  return playinfo["data"]

def download_audio(data, range='0'):
  """
  将音频流保存为本地 m4a 文件。支持通过 Range 参数进行部分下载。

  :param data: get_playinfo_data 返回的 data 字典
  :type data: dict
  :param range: 字节下载范围，默认为 '0' (全量)。例如 '0-1024'
  :type range: str
  :raise requests.ConnectionError: 网络请求音频流失败时抛出
  """
  baseUrl = data['dash']['audio'][0]['baseUrl']
  filename = f"{data['title']}.m4a"
  filepath = os.path.join(AUDIO_PATH, filename)
  os.makedirs('Audio',exist_ok=True)
  headers = {**HEADERS}
  if range != '0':
    headers["Range"] = f"bytes={range}"
  
  response = Session.get(baseUrl, headers=headers, stream=True)
  if response.status_code in [200, 206]:
    print(f"正在下载音频: {filename}")
  else:
    raise requests.ConnectionError(f"音频流下载失败，状态码: {response.status_code}")
      
  with open(filepath, 'wb') as f:
    for chunk in response.iter_content(1024*1024):
      f.write(chunk)
  
  # 如果是部分下载，需要修复时长元数据
  if range != '0':
    fix_audio_duration(filepath)
  print(f"音频保存成功: {filepath}")
  return filepath

def download_videoshot(URL):
  """
  通过 B 站内部 API 获取视频的所有快照图 (Videoshot)。
  快照通常是多幅图像合成的一张或多张大图，可用于 AI 关键帧总结。
  
  :param URL: B 站视频链接
  :type URL: str
  :raise requests.ConnectionError: API 请求或图像下载失败时抛出
  """
  Bvid = get_Bvid(URL)
  Session.headers.update(HEADERS)
  
  response = Session.get(f"https://api.bilibili.com/x/player/videoshot?bvid={Bvid}")
  if response.status_code == 200:
    data = response.json()
    if data['code'] != 0:
      raise requests.ConnectionError(f"API 业务报错: {data['message']}")
      
    images = data["data"]["image"]
    for i, image_url in enumerate(images, start=1):
      if image_url.startswith("//"):
        image_url = f"https:{image_url}"
      
      resp_img = Session.get(image_url)
      if resp_img.status_code == 200:
        dirpath = os.path.join(VIDEOSHOT_PATH, Bvid)
        os.makedirs(dirpath, exist_ok=True)
        filepath = os.path.join(dirpath, f"{Bvid}_shot_{i}.jpg")
        with open(filepath, 'wb') as f:
          f.write(resp_img.content)
        print(f"快照已保存: {filepath}")
      else:
        print(f"第 {i} 张快照下载失败。")
  else:
    raise requests.ConnectionError("无法连接到 Videoshot API。")

def download_subtitle(URL):
  """
  自动检索视频的所有内置外挂字幕，并将其格式化为纯文本 (.txt) 保存。
  优先寻找中文字幕进行下载。
  
  :param URL: B 站视频链接
  :type URL: str
  :raise requests.ConnectionError: API 请求失败或无法解析字幕链接时抛出
  """
  os.makedirs("Subtitles", exist_ok=True)
  Bvid = get_Bvid(URL)
  cid_list = get_cid(URL)
  if not cid_list:
    return
      
  cid = cid_list[0]['cid']
  api_url = f"https://api.bilibili.com/x/player/v2?bvid={Bvid}&cid={cid}"
  response = Session.get(api_url)
  data = response.json()
  
  if data['code'] == 0:
    subtitles = data['data'].get('subtitle', {}).get('subtitles', [])
    if not subtitles:
      print("该视频未检测到内置字幕。")
      return
          
    for subtitle in subtitles:
      lan = subtitle['lan']
      print(f"发现字幕语言: {lan}")
      
      # 过滤或选择特定语言（此处保留 zh-Hans 等中文）
      if 'zh' in lan:
        subtitle_url = subtitle.get('subtitle_url', '')
        if not subtitle_url: continue
              
        full_url = "https:" + subtitle_url
        sub_resp = Session.get(full_url)
        body = sub_resp.json().get('body', [])
        
        # 提取字幕文本内容并去重
        processed_text = [item['content'] for item in body]
        
        dirpath = os.path.join("Subtitles", Bvid)
        os.makedirs(dirpath, exist_ok=True)
        filepath = os.path.join(dirpath, f"{lan}.txt")
        
        with open(filepath, 'w', encoding='utf-8') as f:
          f.write('\n'.join(processed_text))
        print(f"已保存字幕: {filepath}")
  else:
    raise requests.ConnectionError(f"请求播放器数据失败: {data.get('message')}")

#https://www.bilibili.com/video/BV1d1ktBCEaJ/?spm_id_from=333.1007.tianma.1-3-3.click&vd_source=ede24bcc29b6f6c3df591e75217018c8
if __name__ == "__main__":
  log = BilibiliLoginManager()
  log.check_login_status()
  Session.headers.update(HEADERS)
  Session.cookies.update(log.get_cookies())
  download_subtitle("https://www.bilibili.com/video/BV1gAN9euEez?spm_id_from=333.788.recommend_more_video.-1&trackid=web_related_0.router-related-2206146-mbfvr.1769517163115.152&vd_source=ede24bcc29b6f6c3df591e75217018c8")
  #playinfo_data = get_playinfo_data(URL)
  #baseUrl = playinfo_data["dash"]["audio"][0]["baseUrl"]
  #index_range = playinfo_data["dash"]["audio"][0]["SegmentBase"]["indexRange"]
  #download_audio(playinfo_data,"0-126373")
  #Audio = BilibiliStream(baseUrl,index_range)
  #Audio.load_index()
  #print(Audio.cal_duration(),playinfo_data["dash"]["duration"])
  #audio_segments = Audio.get_segments()
  #print(audio_segments[0],audio_segments[1],audio_segments[2])

