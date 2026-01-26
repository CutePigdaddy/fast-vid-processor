import ffmpeg
import os
from typing import Dict, List, Optional, Tuple

os.environ["DISABLE_MODEL_SOURCE_CHECK"]='True'

class Separator:
    """
    视频轨道分离工具类，提供音频提取和字幕导出功能。
    """
    def __init__(self):
        # 初始化不再绑定具体文件，作为一个通用的工具类
        pass

    def _prepare_paths(self, input_path: str, output_dir: Optional[str] = None) -> Tuple[str, str, str]:
        """
        内部辅助函数：计算输出文件名和确定存放目录。
        """
        name = os.path.splitext(os.path.basename(input_path))[0]
        
        # 确定基础输出路径
        if output_dir is None:
            audiotrack_path = "./separate_audiotrack/"
            subtitle_path = "./separate_subtitle/"
        else:
            audiotrack_path = os.path.join(output_dir, "separate_audiotrack/")
            subtitle_path = os.path.join(output_dir, "separate_subtitle/")
            
        # 自动创建目录
        for folder in [audiotrack_path, subtitle_path]:
            if not os.path.exists(folder):
                os.makedirs(folder)
                
        return name, audiotrack_path, subtitle_path

    def extract_audio(self, input_path: str, output_dir: Optional[str] = None) -> List[str]:
        """
        提取视频中的所有音频轨道并并行另存为 MP3。

        Args:
            input_path: 输入视频路径。
            output_dir: 指定输出总目录。

        Returns:
            List[str]: 所有提取出的音频文件路径列表。
        """
        name, audio_dir, _ = self._prepare_paths(input_path, output_dir)
        
        probe = ffmpeg.probe(input_path)
        audio_streams = [s for s in probe['streams'] if s['codec_type'] == 'audio']
        
        extracted_files = []
        for i, _ in enumerate(audio_streams):
            out_file = os.path.join(audio_dir, f"{name}_audio_{i}.mp3")
            # map='a:i' 表示提取第 i 路音轨
            ffmpeg.input(input_path).output(out_file, map=f'a:{i}', acodec='libmp3lame').run(overwrite_output=True)
            extracted_files.append(out_file)
        return extracted_files

    def extract_subtitles(self, input_path: str, output_dir: Optional[str] = None) -> List[str]:
        """
        从视频中提取所有内置字幕流并保存为文本文件。

        Args:
            input_path: 输入视频路径。
            output_dir: 指定输出总目录。

        Returns:
            List[str]: 所有提取出的字幕文件路径列表。
        """
        name, _, subtitle_dir = self._prepare_paths(input_path, output_dir)
        
        probe = ffmpeg.probe(input_path)
        subtitle_streams = [s for s in probe['streams'] if s['codec_type'] == 'subtitle']
        
        extracted_files = []
        for i, _ in enumerate(subtitle_streams):
            out_file = os.path.join(subtitle_dir, f"{name}_sub_{i}.txt")
            # 强制使用 srt 格式写入 txt 文件
            try:
                ffmpeg.input(input_path).output(out_file, map=f's:{i}', format='srt').run(overwrite_output=True)
                extracted_files.append(out_file)
            except ffmpeg.Error:
                print(f"字幕轨道 {i} 提取失败（可能是格式不支持直接导出为文本）")
        return extracted_files

    def process(self, input_path: str, output_dir: Optional[str] = None) -> Dict[str, List[str]]:
        """
        全自动化流程：同时分离指定视频的音频和字幕。

        Args:
            input_path: 输入视频路径。
            output_dir: 指定输出总目录。

        Returns:
            Dict[str, List[str]]: 格式如 {"audio": [...], "subtitles": [...]}。
        """
        audio = self.extract_audio(input_path, output_dir)
        subs = self.extract_subtitles(input_path, output_dir)
        return {"audio": audio, "subtitles": subs}
"""模块说明：
DistractModule 提供了从视频文件中提取所有音频轨道和字幕
使用方法:
1. 创建 DistractModule 实例：
   module = DistractModule()
   2. 调用 process 方法，传入视频文件路径和可选的输出目录：
   results = module.process("path/to/video.mp4", output_dir="output/")
    3. 返回结果包含提取的音频和字幕文件路径列表：
    {
         "audio": ["output/separate_audiotrack/video_audio_0.mp3", ...],
         "subtitles": ["output/separate_subtitle/video_sub_0.txt", ...]
    }
"""