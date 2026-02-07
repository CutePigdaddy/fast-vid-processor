import struct
import requests

class BilibiliStream:
  """
  Bilibili 音频/视频流解析对象，专门用于处理 fMP4 (DASH) 格式的媒体索引。
  它能够解析 sidx (Segment Index) 盒子，从而实现对流媒体的“切片级”精准控制与下载。
  """

  def __init__(self, url, index_range) -> None:
    """
    初始化流对象。

    :param url: 媒体流的 baseUrl (通常来自 PlayInfo)
    :type url: str
    :param index_range: 索引数据所在的字节 range，格式如 "0-2600"
    :type index_range: str
    """
    self.url = url
    self.index_range = index_range
    self.headers = {
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
      "Referer": "https://www.bilibili.com/"
    }
    self.segments = [] # 存储格式: [{'id':int, 'start':int, 'end':int, 'duration':float}]

  def load_index(self):
    """
    根据 index_range 范围下载并解析 sidx (Segment index) 字节数据。
    
    :raise requests.exceptions.RequestException: 如果 HTTP 请求返回的不是 206 Partial Content 时抛出
    """
    # 网络请求二进制数据
    headers = {**self.headers, "Range": f"bytes={self.index_range}"}
    response = requests.get(self.url, headers=headers)
    if response.status_code != 206:
      raise requests.exceptions.RequestException(f"HTTP 206 状态码获取失败，得到: {response.status_code}")
    
    binary_data = response.content
    self._parse_sidx(binary_data)
  
  def _parse_sidx(self, data):
    """
    内部私有方法：深度解析 sidx 二进制协议数据。
    
    :param data: 从网络下载的原始索引字节
    :type data: bytes
    :note: 该方法会计算每个切片的字节偏移（start/end）及物理时长（秒），并存入 self.segments。
    """
    self.data_start_pos = int(self.index_range.split('-')[1]) + 1
    # --- 寻找'sidx'定位符 --- #
    sidx_offset = data.find(b'sidx')
    if sidx_offset == -1:
      raise ValueError("数据中未找到 sidx 标识，这可能不是一个合法的 fMP4 切片索引")
    
    # --- 解析 TimeScale (时间基准) --- #
    # struct.unpack_from(">I", data, offset) 表示以大端序读取 4 字节无符号整数
    timescale = struct.unpack_from(">I", data, sidx_offset + 12)[0]

    # --- 解析 Reference_count (切片总数) --- #
    ref_count_offset = sidx_offset + 26
    ref_count = struct.unpack_from(">H", data, ref_count_offset)[0]

    print(f"解析成功: 时间基准 {timescale}, 发现 {ref_count} 个切片。")

    # --- 循环解析切片细节 --- #
    # 每个切片信息占用 12 字节: 4(Size) + 4(Duration) + 4(SAP info)
    cursor = ref_count_offset + 2
    current_byte_offset = self.data_start_pos
    for i in range(ref_count):
      size_raw = struct.unpack_from(">I", data, cursor)[0]
      size = size_raw & 0x7FFFFFFF # 去除最高位标识位

      duration_raw = struct.unpack_from(">I", data, cursor + 4)[0]
      duration_sec = duration_raw / timescale

      self.segments.append({
        "id": i,
        "start": current_byte_offset,
        "end": current_byte_offset + size - 1,
        "duration": round(duration_sec, 3)
      })

      cursor += 12
      current_byte_offset += size
    print("sidx 索引全量解析完成。")
  
  def get_segments(self):
    """
    获取解析后的切片信息列表。
    
    :return: 包含所有切片详情的列表
    :rtype: list
    """
    return self.segments

  def cal_duration(self):
    """
    根据所有已解析切片的时长之和计算视频/音频的总长度。
    
    :return: 总时长（秒）
    :rtype: float
    """
    return sum(item["duration"] for item in self.segments)
