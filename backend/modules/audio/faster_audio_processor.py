import os
import tempfile
import logging
from typing import List, Tuple, Dict, Optional
from pydub import AudioSegment
try:
    from faster_whisper import WhisperModel, BatchedInferencePipeline
except ImportError:
    from faster_whisper import WhisperModel
    BatchedInferencePipeline = None

# 尝试导入 torch 以检测 GPU 可用性；若不可用则设为 None
try:
    import torch
except Exception:
    torch = None

# 导入进度条库
try:
    from tqdm import tqdm
    tqdm_available = True
    logging.info("✅ 进度条库导入成功")
except ImportError:
    tqdm_available = False
    logging.warning("⚠️ 进度条库导入失败，将使用普通输出")

# 导入 AI 支持模块
try:
    from ai_support.ai_support import analyze_transcript
    ai_support_available = True
    logging.info("✅ AI 支持模块导入成功")
except ImportError as e:
    ai_support_available = False
    logging.warning(f"⚠️ AI 支持模块导入失败: {e}")
except Exception as e:
    ai_support_available = False
    logging.warning(f"⚠️ 初始化 AI 支持模块时出错: {e}")

# 配置选项
generate_ai_summary = True  # 是否生成 AI 总结


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioProcessorConfig:
    """音频处理器配置"""
    # 时间配置（毫秒）
    SEGMENT_LENGTH_MS = 15 * 60 * 1000  # 15分钟
    OVERLAP_MS = 30 * 1000  # 30秒
    
    # 输出配置
    TEMP_AUDIO_FORMAT = "wav"
    OUTPUT_ENCODING = "utf-8"


class LongAudioProcessor:
    """
    长音频处理器：将长音频分割为重叠的片段进行Whisper识别，
    并保持原始时间戳的准确性。
    """
    
    def __init__(self, model_size: str = "base", device_override: Optional[str] = None, config: Optional[AudioProcessorConfig] = None):
        """
        初始化处理器
        Args:
            model_size: Whisper模型大小 (tiny, base, small, medium, large)
            config: 自定义配置对象
        """
        try:
            # 支持手动覆盖设备（device_override），例如用于在无法联网时强制使用 CPU 进行测试
            device = "cpu"
            if device_override is not None:
                device = device_override
                logger.info(f"强制使用设备: {device}（由 device_override 指定）")
            else:
                # 自动检测是否有可用 GPU（CUDA）
                if torch is not None:
                    try:
                        if torch.cuda.is_available():
                            device = "cuda"
                            logger.info(f"检测到可用 GPU，使用设备: {device}")
                        else:
                            logger.info("未检测到可用 GPU，使用 CPU 进行推理")
                    except Exception as e:
                        logger.warning(f"检查 CUDA 可用性时出现问题: {e}; 将使用 CPU")
                        device = "cpu"
                else:
                    logger.info("未安装 torch，默认使用 CPU（若 Whisper 依赖 torch，这里会抛出错误）")

            logger.info(f"正在加载 faster-whisper 模型: {model_size} (device={device})")

            # 选择 compute_type：GPU 使用 float16，CPU 尝试 int8（若不可用回退到 float32）
            compute_type = None
            if device == "cuda":
                compute_type = "float16"
            else:
                compute_type = "int8"

            try:
                self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
            except Exception as e:
                logger.warning(f"使用 compute_type={compute_type} 加载模型失败: {e}; 尝试回退到 float32")
                self.model = WhisperModel(model_size, device=device, compute_type="float32")

            # 尝试启用 BatchedInferencePipeline 以支持 batch_size (仅 cuda 有效)
            self.batched_mode = False
            if device == "cuda" and BatchedInferencePipeline is not None:
                try:
                    self.model = BatchedInferencePipeline(model=self.model)
                    self.batched_mode = True
                    logger.info("已启用 BatchedInferencePipeline 批处理优化")
                except Exception as e:
                    logger.warning(f"启用批处理优化失败: {e}")

            # 保存设备信息以备后续使用/日志
            self.device = device
            self.config = config or AudioProcessorConfig()
            logger.info("处理器初始化完成")
        except Exception as e:
            logger.error(f"初始化处理器失败: {e}")
            raise
        
    def split_audio_with_overlap(self, audio_path: str) -> List[Tuple[AudioSegment, int]]:
        """
        将音频分割为重叠的片段
        Args:
            audio_path: 音频文件路径
        Returns:
            List of (audio_segment, start_time_ms) 元组
        Raises:
            FileNotFoundError: 当文件不存在时
            Exception: 当音频加载失败时
        """
        # 验证文件存在
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            raise FileNotFoundError(f"无法找到音频文件: {audio_path}")
        
        try:
            # 加载音频
            logger.info(f"正在加载音频文件: {audio_path}")
            audio = AudioSegment.from_file(audio_path)
            duration_ms = len(audio)
            duration_min = duration_ms / 1000 / 60
            
            logger.info(f"音频总时长: {duration_min:.2f}分钟")
            
            # 如果音频长度小于等于片段长度，直接返回
            if duration_ms <= self.config.SEGMENT_LENGTH_MS:
                logger.info("音频长度较短，不需要分割")
                return [(audio, 0)]
            
            segments = self._perform_audio_segmentation(audio, duration_ms)
            logger.info(f"音频分割完成，共 {len(segments)} 个片段")
            return segments
            
        except Exception as e:
            logger.error(f"音频分割失败: {e}")
            raise
    
    def _perform_audio_segmentation(self, audio: AudioSegment, duration_ms: int) -> List[Tuple[AudioSegment, int]]:
        """
        执行音频分割逻辑
        """
        segments = []
        start_ms = 0
        
        while start_ms < duration_ms:
            # 计算结束时间（不超过音频总长）
            end_ms = min(start_ms + self.config.SEGMENT_LENGTH_MS, duration_ms)
            
            # 提取片段
            segment = audio[start_ms:end_ms]
            segments.append((segment, start_ms))
            
            # 日志输出片段信息
            segment_start_min = start_ms / 1000 / 60
            segment_end_min = (start_ms + len(segment)) / 1000 / 60
            logger.debug(f"片段 {len(segments)}: {segment_start_min:.1f}min - {segment_end_min:.1f}min")
            
            # 计算下一个片段的起始时间（减去重叠部分）
            start_ms = end_ms - self.config.OVERLAP_MS
            
            # 如果剩余部分小于等于重叠部分，则结束
            if duration_ms - start_ms <= self.config.OVERLAP_MS:
                # 如果有剩余，添加最后一段
                if start_ms < duration_ms:
                    last_segment = audio[start_ms:duration_ms]
                    segments.append((last_segment, start_ms))
                break
        
        return segments
    
    def transcribe_segment(self, audio_segment: AudioSegment, 
                          segment_start_ms: int) -> Dict:
        """
        转录单个音频片段，并调整时间戳
        Args:
            audio_segment: 音频片段
            segment_start_ms: 片段的起始时间（毫秒）
        Returns:
            包含转录结果的字典
        """
        temp_path = None
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                suffix=f".{self.config.TEMP_AUDIO_FORMAT}", 
                delete=False
            ) as tmp_file:
                temp_path = tmp_file.name
            
            # 将音频片段导出为指定格式
            audio_segment.export(temp_path, format=self.config.TEMP_AUDIO_FORMAT)
            
            # 准备转录参数
            transcribe_kwargs = {
                "language": "zh",
                # 引导模型使用标点。这里使用陈述句而非指令，既能提示标点又能避免命令式幻觉
                "initial_prompt": "简体中文，句子之间有标点符号，断句清晰。",
                "beam_size": 5,
                "vad_filter": True,
                # 放宽静音阈值到 1000ms。过短的阈值(如500ms)会切断句子中间的停顿，导致上下文丢失，模型无法判断标点
                "vad_parameters": dict(min_silence_duration_ms=2000),
                "condition_on_previous_text": False
            }

            # 如果启用了 BatchedInferencePipeline，则添加 batch_size
            if getattr(self, "batched_mode", False):
                transcribe_kwargs["batch_size"] = 24

            # 使用 faster_whisper 转录（返回 segments iterable 和 info）
            logger.debug(f"正在转录临时文件: {temp_path}")
            segments_iter, info = self.model.transcribe(temp_path, **transcribe_kwargs)

            segments_list = list(segments_iter)
            segment_start_s = segment_start_ms / 1000.0
     
            # 构建与原来兼容的 result 字典
            result_segments = []
            for seg in segments_list:
                result_segments.append({
                    "start": seg.start + segment_start_s,
                    "end": seg.end + segment_start_s,
                    "text": seg.text
                })

            result = {
                "text": " ".join([s["text"] for s in result_segments]),
                "segments": result_segments,
                "language": getattr(info, "language", None) if info is not None else None
            }

            logger.debug(f"片段转录完成，包含 {len(result.get('segments', []))} 条")
            return result
            
        except Exception as e:
            logger.error(f"转录片段失败: {e}")
            raise
        finally:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"删除临时文件失败: {e}")
    
    def merge_transcriptions(self, all_results: List[Dict]) -> Dict:
        """
        合并所有转录结果，处理重叠部分
        Args:
            all_results: 所有转录结果的列表
        Returns:
            合并后的转录结果
        """
        if not all_results:
            logger.warning("没有转录结果需要合并")
            return {"text": "", "segments": []}
        
        if len(all_results) == 1:
            logger.info("仅有一个转录结果，直接返回")
            return all_results[0]
        
        try:
            # 收集所有片段
            all_segments = []
            for result in all_results:
                if "segments" in result:
                    all_segments.extend(result["segments"])
            
            # 按开始时间排序
            all_segments.sort(key=lambda x: x["start"])
            
            # 处理重叠部分
            merged_segments = self._merge_overlapping_segments(all_segments)
            
            # 合并文本
            full_text = " ".join([seg["text"] for seg in merged_segments])
            
            logger.info(f"合并完成，共 {len(merged_segments)} 个片段")
            
            return {
                "text": full_text,
                "segments": merged_segments,
                "language": all_results[0].get("language", "unknown")
            }
        except Exception as e:
            logger.error(f"合并转录结果失败: {e}")
            raise
    
    def _merge_overlapping_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        处理重叠的转录片段
        """
        merged_segments = []
        last_end = 0
        overlap_count = 0
        
        for segment in segments:
            start = segment["start"]
            end = segment["end"]
            
            # 如果这个片段在前一个片段结束后才开始
            if start >= last_end or not merged_segments:
                merged_segments.append(segment)
                last_end = end
            else:
                # 计算重叠
                overlap = last_end - start
                if overlap > 0:
                    overlap_count += 1
                    logger.debug(f"检测到重叠: {overlap:.2f}秒，跳过此片段")
        
        if overlap_count > 0:
            logger.info(f"检测到 {overlap_count} 个重叠片段，已处理")
        
        return merged_segments
    
    def process_long_audio(self, audio_path: str) -> Dict:
        """
        主处理函数：处理长音频
        Args:
            audio_path: 音频文件路径
        Returns:
            转录结果字典
        """
        logger.info("=" * 60)
        logger.info("开始处理长音频...")
        logger.info("=" * 60)
        
        try:
            # 1. 分割音频
            segments = self.split_audio_with_overlap(audio_path)
            
            # 2. 转录每个片段
            all_results = []
            for i, (segment, start_time) in enumerate(segments, 1):
                logger.info(f"转录片段 {i}/{len(segments)} (原始时间: {start_time/1000:.1f}s)...")
                result = self.transcribe_segment(segment, start_time)
                all_results.append(result)
            
            # 3. 合并结果
            logger.info("合并所有转录结果...")
            final_result = self.merge_transcriptions(all_results)
            
            logger.info("=" * 60)
            logger.info("✅ 处理完成！")
            logger.info(f"总识别段落数: {len(final_result['segments'])}")
            logger.info(f"总文本长度: {len(final_result['text'])} 字符")
            logger.info("=" * 60)
            
            return final_result
            
        except Exception as e:
            logger.error(f"处理音频失败: {e}")
            raise
    
    def save_transcription_with_timestamps(self, result: Dict, output_path: str) -> None:
        """
        保存带时间戳的转录结果
        Args:
            result: 转录结果字典
            output_path: 输出文件路径
        """
        try:
            with open(output_path, "w", encoding=self.config.OUTPUT_ENCODING) as f:
                # 写入摘要信息
                f.write(f"# 音频转录结果\n")
                f.write(f"语言: {result.get('language', '未知')}\n")
                f.write(f"总段落数: {len(result['segments'])}\n\n")
                
                # 写入带时间戳的文本
                f.write("## 时间戳文本\n")
                for seg in result["segments"]:
                    time_str = self._format_timestamp_range(seg["start"], seg["end"])
                    f.write(f"\n[{time_str}] {seg['text']}")
            
            logger.info(f"结果已保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存转录结果失败: {e}")
            raise
    
    @staticmethod
    def _format_timestamp_range(start: float, end: float) -> str:
        """格式化时间戳范围"""
        def format_time(seconds: float) -> str:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes:02d}:{secs:06.3f}"
        
        return f"{format_time(start)} - {format_time(end)}"

def process_audio(audio_path: str, model_size: str = "medium", device_override: Optional[str] = None) -> Dict:
    """处理音频并保存转录结果。

    Args:
        audio_path: 音频文件路径
        model_size: Whisper 模型大小（tiny, base, small, medium, large）

    Returns:
        转录结果字典
    """
    try:
        # 初始化处理器
        logger.info("初始化音频处理器...")
        processor = LongAudioProcessor(model_size=model_size, device_override=device_override)

        result = processor.process_long_audio(audio_path)

        # 确保 output 文件夹存在
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_file = os.path.join(output_dir, f"{base_name}_transcription_with_timestamps.txt")
        processor.save_transcription_with_timestamps(result, output_file)

        # 生成 AI 总结
        if generate_ai_summary and ai_support_available:
            logger.info("=" * 60)
            logger.info("🤖 开始生成 AI 总结...")
            logger.info("=" * 60)
            try:
                import time
                start_time = time.time()
                
                # 使用进度条显示处理过程
                if tqdm_available:
                    # 模拟进度条，因为 analyze_transcript 是一个阻塞调用
                    with tqdm(total=100, desc="AI 处理中", unit="%") as pbar:
                        # 初始化
                        pbar.update(10)
                        pbar.set_postfix(status="初始化 AI 服务")
                        time.sleep(0.5)
                        
                        # 处理中
                        pbar.update(30)
                        pbar.set_postfix(status="分析文本内容")
                        time.sleep(0.5)
                        
                        # 调用 AI 服务
                        pbar.update(40)
                        pbar.set_postfix(status="调用 AI 模型")
                        summary_result = analyze_transcript(output_file)
                        
                        # 完成
                        pbar.update(20)
                        pbar.set_postfix(status="生成总结报告")
                        time.sleep(0.5)
                else:
                    # 无进度条时直接调用
                    logger.info("处理中...")
                    summary_result = analyze_transcript(output_file)
                
                end_time = time.time()
                elapsed_time = end_time - start_time
                
                logger.info(f"✅ AI 总结生成成功！")
                logger.info(f"⏱️  处理时间: {elapsed_time:.2f} 秒")
                logger.info(f"📄 总结文件: {summary_result.get('output_file', '未知')}")
                logger.info(f"📊 总结长度: {summary_result.get('summary_length', 0):,} 字符")
                logger.info(f"📈 原始文本长度: {summary_result.get('text_length', 0):,} 字符")
                logger.info(f"🔧 使用模板: {summary_result.get('template_used', '未知')}")
                logger.info(f"🤖 AI 模型: {summary_result.get('ai_model', '未知')}")
                logger.info("=" * 60)
            except Exception as e:
                logger.error(f"❌ 生成 AI 总结失败: {e}")
                logger.warning("音频转录已完成，但 AI 总结生成失败")
                logger.info("=" * 60)
        elif not generate_ai_summary:
            logger.info("⚠️ AI 总结生成已禁用，跳过总结生成")
        else:
            logger.info("⚠️ AI 支持模块不可用，跳过总结生成")

        logger.info("前3个片段示例:")
        for i, seg in enumerate(result.get("segments", [])[:3], 1):
            preview = seg.get("text", "")[:50] + ("..." if len(seg.get("text", "")) > 50 else "")
            logger.info(f"  {i}. [{seg.get('start', 0):.2f}s - {seg.get('end', 0):.2f}s]: {preview}")

        return result

    except FileNotFoundError as e:
        logger.error(f"文件未找到: {e}")
        raise
    except Exception as e:
        logger.error(f"发生错误: {e}")
        raise


if __name__ == "__main__":
    # 示例调用：修改为实际音频路径和所需模型
    sample_audio = "C:\\Users\\15352\\Desktop\\test1\\第14课 价值底线：什么是“三观一致”？.mp3"
    
    # 默认：自动检测 GPU（若可用）或使用 CPU
    process_audio(sample_audio, model_size="medium")
    
    # 强制使用 CPU 进行测试（用于调试或在无法联网的环境中）：
    # process_audio(sample_audio, model_size="medium", device_override="cpu")
    
    # 强制使用 GPU：
    # process_audio(sample_audio, model_size="medium", device_override="cuda")