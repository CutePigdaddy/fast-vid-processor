import os
import logging
from typing import Optional
from audio_separator.separator import Separator

# 配置日志
logger = logging.getLogger(__name__)

def distractor(input_path: str, output_dir: Optional[str] = None) -> Optional[str]:
    """
    使用 AI 模型从音频中提取人声（原始版）。
    """
    input_path = os.path.abspath(input_path)
    output_dir = os.path.abspath(output_dir) if output_dir else os.path.abspath("./distract_output/")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(input_path):
        logger.error(f"找不到输入文件: {input_path}")
        return None

    try:
        logger.info(f"正在开始人声分离 (高保真加速模式): {os.path.basename(input_path)}")
        
        # 高保真平衡配置：
        # 1. overlap = 0.25：这是兼顾效果与性能的“甜点”值。它能消除分段连接处的电流音或突兀感，保证提取质量。
        # 2. batch_size = 12：由于开启了 overlap，计算开销和内存占用会上升，
        #    我们将 batch 从 16 略微降到 12，以确保你的 16GB 物理内存不会溢出导致系统卡顿。
        mdx_params = {
            "hop_length": 1024,
            "segment_size": 256, 
            "overlap": 0.25,
            "batch_size": 16, 
        }

        separator = Separator(
            output_format="mp3",
            output_single_stem="Vocals",
            output_dir=output_dir,
            log_level=logging.WARNING,
            mdx_params=mdx_params
        )
        
        # 加载默认模型
        separator.load_model(model_filename="UVR-MDX-NET-Inst_HQ_5.onnx")
        
        # 执行分离
        output_files = separator.separate(audio_file_path=input_path)
        
        if not output_files:
            logger.error("分离结果为空")
            return None

        # 查找包含 Vocals 的文件
        vocals_file = next((f for f in output_files if "Vocals" in f), output_files[0])
        full_path = vocals_file if os.path.isabs(vocals_file) else os.path.join(output_dir, vocals_file)
        
        if os.path.exists(full_path):
            logger.info(f"分离成功: {full_path}")
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



