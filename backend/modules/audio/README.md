# 音频处理模块 (Audio Processor Module)

## 📋 模块概述

该模块提供**长音频自动分割与转录**功能，基于 OpenAI 的 Whisper 模型。主要特点包括：

- ✅ **智能音频分割**：自动将长音频分割为可管理的片段（默认15分钟），并保持30秒的重叠以确保内容连续性
- ✅ **精确时间戳**：保留所有转录文本的原始时间戳，无论音频长度
- ✅ **GPU/CPU自动检测**：智能识别可用硬件，自动选择最优计算方式
- ✅ **灵活配置**：支持自定义片段长度、重叠时间、模型大小等参数
- ✅ **流式处理**：使用 faster-whisper 的迭代器，降低内存占用
- ✅ **详细日志**：完整的处理日志，方便调试和监控

## 🏗️ 核心组件

### `AudioProcessorConfig` 类

音频处理器的配置容器，包含所有可配置参数：

```python
class AudioProcessorConfig:
    SEGMENT_LENGTH_MS = 15 * 60 * 1000  # 15分钟一个片段
    OVERLAP_MS = 30 * 1000              # 片段间重叠30秒
    TEMP_AUDIO_FORMAT = "wav"           # 临时文件格式
    OUTPUT_ENCODING = "utf-8"           # 输出文件编码
```

**可自定义字段说明：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SEGMENT_LENGTH_MS` | 900000 (15分钟) | 单个音频片段长度（毫秒） |
| `OVERLAP_MS` | 30000 (30秒) | 相邻片段重叠时长（毫秒） |
| `TEMP_AUDIO_FORMAT` | `wav` | 临时文件格式 |
| `OUTPUT_ENCODING` | `utf-8` | 输出文本编码 |

### `LongAudioProcessor` 类

主处理器类，负责音频分割、转录和结果合并。

#### 初始化方法
```python
LongAudioProcessor(
    model_size: str = "base",
    device_override: Optional[str] = None,
    config: Optional[AudioProcessorConfig] = None
)
```

**参数说明：**
- `model_size`：Whisper 模型大小
  - `tiny`：最小模型，速度快，精度低
  - `base`：平衡方案（推荐用于测试）
  - `small`：中等模型
  - `medium`：较大模型，精度高（推荐用于生产环境）
  - `large`：最大模型，精度最高（需要大量显存）

- `device_override`：强制指定计算设备
  - `None`：自动检测（推荐）
  - `"cuda"`：强制使用 GPU
  - `"cpu"`：强制使用 CPU

- `config`：自定义配置对象，若为 `None` 则使用默认配置

#### 主要方法

| 方法 | 功能 | 返回值 |
|------|------|--------|
| `process_long_audio(audio_path)` | 处理长音频的主入口 | `Dict` 包含完整转录结果 |
| `split_audio_with_overlap(audio_path)` | 分割音频 | `List[Tuple]` 音频片段和起始时间 |
| `transcribe_segment(segment, start_ms)` | 转录单个片段 | `Dict` 包含转录结果和时间戳 |
| `merge_transcriptions(results)` | 合并多个转录结果 | `Dict` 合并后的完整结果 |
| `save_transcription_with_timestamps(result, path)` | 保存带时间戳的结果 | 无 |

## 📊 数据结构

### 转录结果格式

```python
{
    "text": "完整的转录文本...",  # 所有片段的文本合并
    "segments": [
        {
            "start": 0.0,       # 起始时间（秒）
            "end": 5.23,        # 结束时间（秒）
            "text": "转录内容"   # 该片段的文本
        },
        # 更多片段...
    ],
    "language": "zh"            # 检测到的语言代码
}
```

## 🚀 使用示例

### 基础使用

```python
from modules.audio.faster_audio_processor import process_audio

# 简单处理（自动检测 GPU，使用 medium 模型）
result = process_audio(
    audio_path="path/to/your/audio.mp3",
    model_size="medium"
)

# 结果已自动保存为：audio_transcription_with_timestamps.txt
print(result["text"])  # 获取完整转录文本
```

### 高级使用（自定义配置）

```python
from modules.audio.faster_audio_processor import (
    LongAudioProcessor, 
    AudioProcessorConfig
)

# 自定义配置：20分钟片段，45秒重叠
custom_config = AudioProcessorConfig()
custom_config.SEGMENT_LENGTH_MS = 20 * 60 * 1000
custom_config.OVERLAP_MS = 45 * 1000

# 创建处理器实例
processor = LongAudioProcessor(
    model_size="medium",
    device_override="cuda",  # 强制使用 GPU
    config=custom_config
)

# 处理音频
result = processor.process_long_audio("path/to/audio.mp3")

# 保存结果
processor.save_transcription_with_timestamps(result, "output.txt")
```

### CPU 强制模式（测试/调试）

```python
from modules.audio.faster_audio_processor import process_audio

# 在无法联网或需要测试时强制使用 CPU
result = process_audio(
    audio_path="path/to/audio.mp3",
    model_size="base",  # 使用较小模型
    device_override="cpu"
)
```

### 直接使用类方法（更细粒度控制）

```python
from modules.audio.faster_audio_processor import LongAudioProcessor

processor = LongAudioProcessor(model_size="medium")

# 1. 分割音频
segments = processor.split_audio_with_overlap("audio.mp3")
print(f"分割成 {len(segments)} 个片段")

# 2. 逐个转录
all_results = []
for i, (segment, start_time) in enumerate(segments, 1):
    print(f"处理片段 {i}/{len(segments)}...")
    result = processor.transcribe_segment(segment, start_time)
    all_results.append(result)

# 3. 合并结果
final_result = processor.merge_transcriptions(all_results)

# 4. 保存结果
processor.save_transcription_with_timestamps(final_result, "output.txt")
```

## 📦 依赖项

| 依赖包 | 版本要求 | 用途 |
|--------|---------|------|
| `faster-whisper` | ≥0.7.0 | 语音识别核心库 |
| `pydub` | ≥0.25.0 | 音频处理 |
| `torch` | ≥1.9.0 (可选) | GPU 加速（仅 CUDA 模式需要） |

**安装依赖：**
```bash
pip install faster-whisper pydub torch  # 包含 GPU 支持
pip install faster-whisper pydub       # 仅 CPU 模式
```

**额外系统依赖：**
- `ffmpeg`（pydub 需要）
  - Windows: `choco install ffmpeg` 或从 [ffmpeg.org](https://ffmpeg.org) 下载
  - macOS: `brew install ffmpeg`
  - Linux: `apt-get install ffmpeg`

## 💻 硬件要求

| 配置 | 最小要求 | 推荐配置 |
|------|---------|---------|
| **CPU 模式** | 8GB RAM, 4核CPU | 16GB RAM, 8核CPU |
| **GPU 模式 (CUDA)** | 4GB VRAM | 8GB+ VRAM (RTX 3060 或更好) |
| **模型大小** | base (1.4GB) | medium (3.1GB) |

## ⏱️ 性能指标

基于不同配置的处理速度参考：

| 模型 | GPU (RTX 3080) | CPU (16核) | 说明 |
|------|--------|-------|------|
| tiny | 5x | 0.5x | 实时速度的 5 倍 |
| base | 3x | 0.3x | 实时速度的 3 倍 |
| small | 2x | 0.2x | 实时速度的 2 倍 |
| medium | 1x | 0.1x | 接近实时 |
| large | 0.5x | - | 1 小时音频需 2 小时 |

> **x 表示相对于音频实际时长的倍数**。例如，"3x" 表示 1 小时音频需要 20 分钟处理。

## 🔧 常见问题

### Q1: 如何处理 "No module named 'torch'" 错误？
**A:** `torch` 是可选依赖，仅用于 GPU 检测。若无需 GPU 支持，可以忽略此错误。若需要 GPU，请安装：
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Q2: 如何判断是否在使用 GPU？
**A:** 查看输出日志。如果看到 `检测到可用 GPU，使用设备: cuda`，说明正在使用 GPU。

### Q3: 处理特别长的音频时内存溢出怎么办？
**A:** 有以下几个方案：
1. 减小模型大小：`model_size="base"` 而不是 `"large"`
2. 减小片段长度：`SEGMENT_LENGTH_MS = 10 * 60 * 1000`（10分钟）
3. 使用 CPU 模式：`device_override="cpu"`
4. 增加系统内存/显存

### Q4: 转录准确率不够高？
**A:** 尝试以下改进方案：
1. 使用更大的模型：`model_size="large"`
2. 确保音频质量良好（16kHz 采样率，单声道或立体声）
3. 调整 `initial_prompt` 参数提供上下文提示
4. 增加 `beam_size` 参数值（默认5，可增加到10）

### Q5: 支持哪些音频格式？
**A:** pydub 支持所有常见格式：`mp3`, `wav`, `m4a`, `ogg`, `flac`, `aac` 等。

### Q6: 时间戳准确吗？
**A:** 是的。模块会精确追踪每个片段的起始时间并调整 Whisper 返回的相对时间戳为绝对时间戳，确保整个音频的时间戳准确。

## 📝 输出文件格式

保存的转录文件格式示例：

```markdown
# 音频转录结果
语言: zh
总段落数: 15

## 时间戳文本

[00:00.000 - 00:05.230] 这是第一段转录内容...

[00:05.500 - 00:12.100] 这是第二段转录内容...

## 完整文本
这是第一段转录内容... 这是第二段转录内容...
```

## 🐛 调试技巧

**启用详细日志：**
```python
import logging

# 在导入模块前设置日志级别
logging.basicConfig(level=logging.DEBUG)

from modules.audio.faster_audio_processor import process_audio
result = process_audio("audio.mp3")  # 会输出详细的调试信息
```

**检查处理进度：**
通过日志输出可以看到实时的处理进度，每个片段的处理时间、合并情况等。

## 📖 API 参考

详见 [faster_audio_processor.py](./faster_audio_processor.py) 中的详细 docstring 文档。

## 🤝 贡献指南

如需改进此模块，请注意：
1. 保持与 Whisper/faster-whisper API 的兼容性
2. 添加详细的日志信息
3. 完善错误处理和异常捕获
4. 更新本 README 文档

## 📄 许可证

本模块遵循项目主许可证。

---

**最后更新**：2026年1月27日  
**维护者**：CutePigdaddy
