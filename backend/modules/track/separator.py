import ffmpeg
import os
import logging
from typing import Dict, List, Optional, Tuple

# 配置日志
logger = logging.getLogger(__name__)


class Separator:
    """
    视频轨道分离工具类，提供音频提取和字幕导出功能。
    """
    def __init__(self):
        # 初始化不再绑定具体文件，作为一个通用的工具类
        os.environ["DISABLE_MODEL_SOURCE_CHECK"]='True'
        logger.debug("Separator 工具类已初始化")
    def _prepare_paths(self, input_path: str, output_dir: Optional[str] = None) -> Tuple[str, str]:
        """
        内部辅助函数：计算文件名基础并确定输出目录。
        """
        name = os.path.splitext(os.path.basename(input_path))[0]
        
        # 如果未指定 output_dir，则使用当前目录下的默认文件夹
        if output_dir is None:
            output_dir = "./output"
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"创建输出目录: {output_dir}")
                
        return name, output_dir

    def extract_audio(self, input_path: str, output_dir: Optional[str] = None) -> List[str]:
        """
        提取视频中的所有音频轨道并另存为 MP3。
        """
        name, audio_dir = self._prepare_paths(input_path, output_dir)
        
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"输入文件不存在: {input_path}")
            raise FileNotFoundError(f"Input file does not exist: {input_path}")
        
        try:
            probe = ffmpeg.probe(input_path)
        except Exception as e:
            logger.error(f"探测视频流失败: {str(e)}")
            raise RuntimeError(f"Failed to probe file {input_path}: {str(e)}") from e
            
        audio_streams = [s for s in probe['streams'] if s['codec_type'] == 'audio']
        
        extracted_files = []
        for i, _ in enumerate(audio_streams):
            out_file = os.path.join(audio_dir, f"{name}_track_{i}.mp3")
            logger.info(f"提取音轨 -> {os.path.basename(out_file)}")
            ffmpeg.input(input_path).output(
                out_file, 
                map=f'a:{i}', 
                acodec='libmp3lame',
                ar='44100',
                audio_bitrate='128k'
            ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
            extracted_files.append(out_file)
        
        return extracted_files

    def extract_subtitles(self, input_path: str, output_dir: Optional[str] = None) -> List[str]:
        """
        从视频中提取所有内置字幕流。
        """
        name, subtitle_dir = self._prepare_paths(input_path, output_dir)

        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            logger.error(f"输入文件不存在: {input_path}")
            return []

        try:
            probe = ffmpeg.probe(input_path)
        except Exception as e:
            logger.error(f"探测视频流失败: {str(e)}")
            return []

        subtitle_streams = [s for s in probe['streams'] if s['codec_type'] == 'subtitle']

        extracted_files = []
        for i, _ in enumerate(subtitle_streams):
            out_file = os.path.join(subtitle_dir, f"{name}_sub_{i}.txt")
            logger.info(f"正在导出字幕轨道 {i} -> {os.path.basename(out_file)}")
            # 强制使用 srt 格式写入 txt 文件
            try:
                ffmpeg.input(input_path).output(out_file, map=f's:{i}', format='srt').run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
                extracted_files.append(out_file)
            except ffmpeg.Error:
                logger.warning(f"字幕轨道 {i} 提取失败（可能是格式不支持直接导出为文本）")
            except Exception as e:
                logger.warning(f"导出字幕轨道 {i} 时发生错误: {str(e)}")
                continue

        logger.info(f"字幕提取任务结束，成功提取 {len(extracted_files)} 路")
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
        logger.info(f"开始全自动化流任务: {input_path}")
        audio = self.extract_audio(input_path, output_dir)
        subs = self.extract_subtitles(input_path, output_dir)
        logger.info("全自动化任务处理完成")
        return {"audio": audio, "subtitles": subs}

