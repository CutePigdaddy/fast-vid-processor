from audio_separator.separator import Separator
import os
from typing import Optional

MODEL_PATH= "UVR-MDX-NET-Inst_HQ_5.onnx"

def distractor(input_path: str, output_dir: Optional[str] = None) -> Optional[str]:
    """
    使用 AI 模型分离视频或音频中的人声轨道。

    该函数调用 UVR-MDX-NET 模型进行高质量人声提取，支持多种音视频格式输入。

    Args:
        input_path (str): 输入文件的绝对或相对路径。
        output_dir (str, optional): 本次处理的输出文件夹。若不提供，默认存放在 `./distract_output/`。

    Returns:
        Optional[str]: 成功则返回生成的人声 MP3 文件完整路径，失败则返回 None。

    Example:
        >>> from modules.track.distract import distractor
        >>> vocal_path = distractor("vlog.mp4", "./results")
        >>> print(vocal_path)
    """
    os.environ["DISABLE_MODEL_SOURCE_CHECK"]='True'
    if output_dir is None:
        output_dir="./distract_output/"
    else:
        output_dir = output_dir

    # 防御性编程：确保输出目录存在，防止找不到路径报错
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 防御性编程：检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误：找不到输入文件 {input_path}")
        return None

    try:
        # 优化：移除 use_soundfile=True 参数，直接使用 MP3 格式
        separator = Separator(
            output_format="mp3",
            output_single_stem="Vocals",
            output_dir=output_dir,
            mdx_params={
                "hop_length": 1024,
                "segment_size": 256,
                "overlap": 0.1,
                "batch_size": 1,
                "enable_denoise": True
            }
        )
        separator.load_model(model_filename=MODEL_PATH)
        
        filename = os.path.basename(input_path)
        name = os.path.splitext(filename)[0]
        
        separator.separate(audio_file_path=input_path)
        
        mp3_output_path = os.path.join(output_dir, f"{name}_Vocals.mp3")
        
        print(f"分离人声和背景完成，输出文件夹：{output_dir}")
        return mp3_output_path
            
    except Exception as e:
        # 捕获可能的 AI 模型执行错误或权限错误
        print(f"分离过程中出现意外错误: {e}")
        return None  

"""调用方法:
    返回的是输出文件的路径
"""
    

