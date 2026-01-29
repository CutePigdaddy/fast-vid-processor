# Fast Video Processor (FastVidProcessor)

一个高效的音视频处理框架，旨在实现视频到文字的自动化转录。该项目集成了音轨提取、人声分离、音频压缩以及基于 `faster-whisper` 的长音频转录功能。

## 🚀 主要功能

- **离线视频批量处理**：支持遍历文件夹，自动提取视频音轨并转换为带时间戳的文本。
- **在线视频转码**：支持通过 URL（如 Bilibili）直接下载音频并进行转录处理。
- **人声分离与增强**：通过 `modules/track` 模块分离背景音乐与人声，提取纯净语音。
- **高效转录**：利用 `faster-whisper` (Whisper medium 模型) 实现高性能的语音识别。
- **视觉辅助 (准备中)**：内置关键帧提取与 OCR 识别模块，可用于提取视频中的文本信息。

## 📦 安装说明

### 1. 环境要求
- Python 3.10+
- **FFmpeg**: 请确保系统中已安装 FFmpeg。

### 2. 安装依赖
由于包含 PyTorch CUDA 版本和 PaddlePaddle，建议按以下顺序安装：

```bash
# 克隆仓库
git clone https://github.com/CutePigdaddy/fast-vid-processor
cd fast-vid-processor

# 安装主要依赖
pip install -r requirements.txt
```

*注意：如果需要 GPU 加速，请确保安装了匹配的 CUDA 驱动（项目默认配置为 CUDA 12.x）。*

## 🛠️ 快速上手

### 1. 离线批量处理视频
在 `video_to_text.py` 中使用：

```python
from video_to_text import batch_offline_videos

source_dir = "path/to/your/videos"
output_root = "results"
batch_offline_videos(source_dir, output_root)
```

### 2. 在线视频转录 (以 Bilibili 为例)
在 `video_to_text.py` 中使用：

```python
from video_to_text import batch_online_videos

video_url = "https://www.bilibili.com/video/BV1..."
batch_online_videos(video_url, output_root="Audio")
```

## 📂 项目结构

```text
├── modules/
│   ├── audio/   # 音频处理核心 (faster-whisper 封装)
│   ├── online/  # 在线视频爬虫与下载 (Bilibili 等)
│   ├── track/   # 音轨操作 (提取、分离、压缩)
│   └── vision/  # 视觉处理 (关键帧、OCR)
├── video_to_text.py # 主入口脚本
└── requirements.txt # 依赖列表
```

## 📜 许可证
本项目采用 [LICENSE](LICENSE) 中所述的开源协议。

