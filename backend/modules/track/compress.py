import ffmpeg
import os
from typing import Optional

def compresser(input_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    将音频文件压缩并归一化为统一的发布标准。

    参数规格:
    - 采样率: 44.1kHz
    - 码率: 128kbps (CBR)
    - 位深: 16bit (s16p)
    - 格式: MP3

    Args:
        input_path (str): 源音频文件路径。
        output_path (str, optional): 输出 MP3 完整路径。若不提供，则在同一目录下生成 `_compressed.mp3`。

    Returns:
        Optional[str]: 生成完毕的文件路径，若失败则返回 None。
    """
    if output_path is None:
        # 默认在原文件名后加 _normalized
        base, _ = os.path.splitext(input_path)
        output_path = f"{base}_compressed.mp3"
        

    try:
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                ar='44100',        # 采样率 44.1kHz
                audio_bitrate='128k', # 码率 128kbps
                acodec='libmp3lame', # 使用 MP3 编码器
                sample_fmt='s16p'    # 设置位深为 16-bit (planar)
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        print(f"处理完成: {output_path}")
        return output_path
    except ffmpeg.Error as e:
        print(f"FFmpeg 错误: {e.stderr.decode()}")
        return None

# 使用示例
# normalize_audio("test.wav")