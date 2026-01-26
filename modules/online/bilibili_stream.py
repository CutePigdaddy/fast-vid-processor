import struct
import requests

class BilibiliStream:
  """
  Bilibili音轨/视轨对象
  """

  def __init__(self, url, index_range) -> None:
    """
    初始化音轨/视轨对象

    :param url: 音轨/视轨的baseUrl
    :param index_range: html中获取index_range所在字节数
    """
    self.url = url
    self.index_range = index_range
    self.headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
      "Referer": "https://www.bilibili.com/"
    }
    self.segments = []
    #存储格式: [{'offset':int,'size':int,'duration':float}]

  def load_index(self):
    """
    下载解析sidx(Segment index)
    """
    #网络请求二进制数据
    headers = {**self.headers,"Range":f"bytes={self.index_range}"}
    response = requests.get(self.url,headers = headers)
    if response.status_code != 206:
      raise requests.exceptions.RequestException(f"HTTP 206状态码期望失败，得到: {response.status_code}")
    
    binary_data = response.content
    
    #通过后面定义的代码解析二进制数据
    self._parse_sidx(binary_data)
  
  def _parse_sidx(self, data):
    """
    用于解析sidx的内部方法
    
    :param data: sidx二进制数据
    :param index_range: 形如'0-2600'格式的sidx字节范围
    """
    self.data_start_pos = int(self.index_range.split('-')[1])+1
    # --- 寻找'sidx'定位符 --- #
    sidx_offset = data.find(b'sidx') #b指字节序列
    if sidx_offset == -1:
      raise ValueError("数据中未找到 sidx 标识，这可能不是一个合法的 fMP4 切片索引")
    
    # --- 解析TimeScale(时间基准) ---#
    timescale = struct.unpack_from(">I",data,sidx_offset+12)[0]
    #struct.unpack_from(格式, 数据, 偏移量)
    #">I" 表示：大端序读取 4 字节无符号整数
    #返回一个元组(Tuple)


    #---解析Reference_count(切片数量)---#
    ref_count_offset = sidx_offset + 26
    ref_count = struct.unpack_from(">H",data,ref_count_offset)[0]

    print(f"Timescale:{timescale},发现了{ref_count}个切片")

    #---循环解析切片信息---#
    #每一个切片12字节 4 Size 4 Duration 4 SAP info
    cursor = ref_count_offset + 2
    current_byte_offset = self.data_start_pos
    for i in range(ref_count):
      #解析4字节 size
      size_raw = struct.unpack_from(">I",data,cursor)[0]
      size = size_raw & 0x7FFFFFFF
      #去除第一位的标识位

      #解析4字节 duration
      duration_raw = struct.unpack_from(">I",data,cursor+4)[0]
      duration_sec = duration_raw/timescale

      #记录结果
      self.segments.append({
        "id": i,
        "start": current_byte_offset,
        "end": current_byte_offset + size - 1,
        "duration": round(duration_sec,3)
      })

      cursor += 12
      current_byte_offset += size
    print("解析完成！")
  
  def get_segments(self):
    """
    返回切片解析列表
    
    :param self: Bilibilistream实例对象
    """
    return self.segments

  def cal_duration(self):
    all_duration = 0
    for item in self.segments:
      all_duration += item["duration"]
    return all_duration
