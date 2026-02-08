import requests
import json
import time
import qrcode
import logging
import os
Session = requests.Session()
HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
  "Referer": "https://www.bilibili.com"
}
logger = logging.getLogger(__name__)
class BilibiliLoginManager:
  """
  B 站登录管理器，负责账号凭证（Cookies）的自动化获取、持久化保存与可用性校验。
  支持手动输入 Cookie 字符串或通过扫码（二维码）方式登录。
  """
  def __init__(self, cookie_file="cookies.json"):
    """
    初始化登录管理器。
    
    :param cookie_file: 存储 Cookie 文件的路径，默认为当前目录下的 "cookies.json"
    :type cookie_file: str
    """
    self.cookie_file = cookie_file
    self.session = requests.Session()
    self.session.headers.update(HEADERS)
    if os.path.exists(cookie_file):
      with open(cookie_file, 'r') as f:
        cookies = json.load(f)
        self.session.cookies.update(cookies)
        if self.check_login_status() == True:
          logger.info("当前本地登录凭证有效，已自动加载。")
  
  def set_manual_cookies(self, input_cookies):
    """
    手动设置 Cookie。支持字典格式或浏览器复制的原始字符串格式。
    
    :param input_cookies: Cookie 字符串（key=value;...）或字典对象
    :type input_cookies: str or dict
    """
    if isinstance(input_cookies, str):
      cookie_dict = {}
      for item in input_cookies.split(";"):
        if '=' in item:
          key, value = item.strip().split('=', 1)
          cookie_dict[key] = value
      self.session.cookies.update(cookie_dict)
    else:
      self.session.cookies.update(input_cookies)
  
  def _get_qrcode(self) -> str:
    """
    内部方法：从 B 站 API 获取登录二维码 URL 及 Key。
    
    :return: 扫描状态轮询所需的 qrcode_key
    :rtype: str
    :raise requests.ConnectionError: 网络请求异常或 API 返回错误
    """
    URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    
    response = self.session.get(URL)
    resp_json = response.json()
    if resp_json['code'] == 0:
      data = resp_json['data']
      qrcode_url = data['url']
      qrcode_key = data['qrcode_key']
      img = qrcode.make(qrcode_url)
      with open('qrcode.png', 'wb') as f:
        img.save(f)
      print(f"二维码已生成: {os.path.abspath('qrcode.png')}")
      print(f"请使用手机 B 站 APP 扫码，或直接访问链接: {qrcode_url}")
    else:
      raise requests.ConnectionError("二维码生成请求失败。")
    return qrcode_key

  def set_qrcode_cookies(self):
    """
    启动交互式扫码登录流程。
    会在本地保存二维码图片，并持续轮询扫码状态，直到成功登录或过期。
    登录成功后会自动将 Cookies 保存到初始化时指定的文件中。
    """
    qrcode_key = self._get_qrcode()
    if not qrcode_key:
      return
    URL = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}"
    print("正在等待扫码，请在手机端确认...")
    while True:
      response = self.session.get(URL)
      data = response.json().get('data', {})
      code = data.get('code')

      if code == 0:
        print("登录成功！")
        break
      elif code == 86101: # 未扫码
        pass
      elif code == 86090: # 已扫码待确认
        print("已扫码，请在手机端点击确认...")
      elif code == 86038: # 二维码失效
        print("二维码已过期，请重新运行登录程序。")
        return 
      time.sleep(2)
      
    # 登录成功，保存 cookies
    with open(self.cookie_file, 'w') as f:
      json.dump(self.session.cookies.get_dict(), f)
    print(f"登录凭证已持久化到: {self.cookie_file}")

  def check_login_status(self):
    """
    通过调用 B 站导航栏 API 检查当前 Session 中的 Cookie 是否仍然有效。
    
    :return: 有效返回 True，失效或未登录返回 False
    :rtype: bool
    """
    URL = "https://api.bilibili.com/x/web-interface/nav"
    try:
      response = self.session.get(URL)
      data = response.json()
      if data['code'] == 0:
        print(f"登录校验通过！当前用户: {data['data']['uname']}")
        return True
    except Exception:
      pass
    print("当前处于未登录状态或凭证已过期。")
    return False

  def get_cookies(self):
    """
    获取当前管理器中存储的所有 Cookies。
    
    :return: 包含所有 Cookie 键值对的字典
    :rtype: dict
    """
    return self.session.cookies.get_dict()
  
