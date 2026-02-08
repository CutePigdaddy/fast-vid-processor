import os
import logging
from typing import Optional
from audio_separator.separator import Separator

# 配置日志
logger = logging.getLogger(__name__)

# --- 模型单例挂载区域 ---
_GLOBAL_SEPARATOR = None

def _get_initialized_separator(output_dir: str):
    """
    懒加载单例：确保模型在进程生命周期内只加载一次，并在后续调用中复用。
    """
    global _GLOBAL_SEPARATOR
    if _GLOBAL_SEPARATOR is None:
        logger.info("正在执行模型首次常驻挂载 (UVR-MDX-NET)...")
        # 采用高保真平衡配置
        mdx_params = {
            "hop_length": 1024,
            "segment_size": 256, 
            "overlap": 0.25,
            "batch_size": 16, 
        }
        _GLOBAL_SEPARATOR = Separator(
            output_format="mp3",
            output_single_stem="Vocals",
            output_dir=output_dir,
            log_level=logging.WARNING,
            mdx_params=mdx_params
        )
        # 这是最耗时的 IO 和计算操作
        _GLOBAL_SEPARATOR.load_model(model_filename="UVR-MDX-NET-Inst_HQ_5.onnx")
    else:
        # 如果已经加载，仅动态更新当前的输出目录，不重新加载模型
        _GLOBAL_SEPARATOR.output_dir = output_dir
        
    return _GLOBAL_SEPARATOR

def distractor(input_path: str, output_dir: Optional[str] = None) -> Optional[str]:
    """
    使用 AI 模型从音频中提取人声（单例加速版）。
    原有调用逻辑不变，但第二次及以后的调用将省去模型加载时间。
    """
    input_path = os.path.abspath(input_path)
    # 确定实际输出路径
    actual_output_dir = os.path.abspath(output_dir) if output_dir else os.path.abspath("./distract_output/")

    if not os.path.exists(actual_output_dir):
        os.makedirs(actual_output_dir, exist_ok=True)
    
    if not os.path.exists(input_path):
        logger.error(f"找不到输入文件: {input_path}")
        return None

    try:
        logger.info(f"接收到人声分离请求: {os.path.basename(input_path)}")
        
        # 获取常驻内存的模型实例
        separator = _get_initialized_separator(actual_output_dir)
        
        # 执行分离 (由于模型已在内存，此处将立即开始推理)
        output_files = separator.separate(audio_file_path=input_path)
        
        if not output_files:
            logger.error("分离结果为空")
            return None

        # 查找包含 Vocals 的文件
        vocals_file = next((f for f in output_files if "Vocals" in f), output_files[0])
        full_path = vocals_file if os.path.isabs(vocals_file) else os.path.join(actual_output_dir, vocals_file)
        
        if os.path.exists(full_path):
            logger.info(f"分离任务完成: {full_path}")
            return full_path
        else:
            logger.error(f"找不到生成的音频文件: {full_path}")
            return None

    except Exception as e:
        logger.error(f"人声分离过程中发生错误: {e}")
        return None

if __name__ == "__main__":
    # 配置基础日志显示输出
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 测试文件路径 (请确保 D 盘下存在该文件)
    test_file = r"D:\第1节：你决定好要进入婚姻了吗？.mp3"
    test_output = os.path.abspath("./test_distractor")
    
    # 检查 GPU 状态
    try:
        import torch
        logger.info("="*50)
        logger.info(f"CUDA 可用性检查: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"检测到显卡: {torch.cuda.get_device_name(0)}")
            logger.info("程序将尝试使用 GPU 进行加速。")
        else:
            logger.info("未检测到 CUDA，将使用 CPU 运行。")
        logger.info("="*50)
    except ImportError:
        logger.warning("未安装 torch，无法检测 GPU 状态。")

    # 执行人声提取
    result = distractor(test_file, test_output)
    
    if result:
        logger.info(f"测试任务完成！生成文件: {result}")
    else:
        logger.error("测试任务失败，请检查上方日志报错。")



