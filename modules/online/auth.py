import requests
import time
import qrcode
Session = requests.Session()
HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
  "Referer": "https://www.bilibili.com"
}

class BilibiliLoginManager:
  """
  B站登录模块 负责cookie获取、保存与校验
  """
  def __init__(self,cookie_file="cookies.json"):
    self.cookie_file = cookie_file
    self.session = requests.Session()
    self.cookies = {}
    self.session.headers.update(HEADERS)
  
  def set_manual_cookies(self,input_cookies):
    if isinstance(input_cookies,str):
      cookie_dict = {}
      for item in input_cookies.split(";"):
        if '=' in item:
          key,value = item.strip().split('=')
          cookie_dict[key] = value
      self.session.cookies.update(cookie_dict)
    else:
      self.session.cookies.update(input_cookies)
  
  def _get_qrcode(self) -> str:
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
      print("二维码已保存到modules/online/qrcode.png")
      print(f"请扫码保存或者直接通过链接扫码登录{qrcode_url}")
    else:
      raise requests.ConnectionError("二维码请求失败。")
    return qrcode_key

  def set_qrcode_cookies(self):
    qrcode_key = self._get_qrcode()
    if not qrcode_key:
      return
    URL = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}"
    print("正在等待扫码...")
    while True:
      response = self.session.get(URL)
      data = response.json().get('data',{})
      code = data.get('code')

      if code == 0:
        print("登陆成功")
        break
      elif code == 86101:
        pass
      elif code == 86090:
        print("已扫码，请在手机端确认！")
      elif code == 86038:
        print("二维码已失效，请重试")
        return 
      time.sleep(2)


  def check_login_status(self):
    """
    检验当前登陆凭证是否有效
    """
    URL = "https://api.bilibili.com/x/web-interface/nav"
    response = self.session.get(URL)
    data = response.json()

    if data['code'] == 0:
      print(f"登录成功，欢迎用户：{data['data']['uname']}!")
      return True
    else:
      print("登陆失败或者凭证过期")
      return False

  def get_headers(self):
    return {
      "User-Agent": "Mozilla/5.0",
      "Referer": "https://www.bilibili.com/",
      "Cookies": self.session.cookies
    }
  
log = BilibiliLoginManager()
log.set_qrcode_cookies()
log.check_login_status()