import cv2
import os
import numpy as np

def extract_frames(video_path, output_folder, sensitivity=0.01, min_interval=0.5):
    """
    针对文字内容（PPT、字幕、文档）优化的关键帧提取。
    
    :param video_path: 视频路径
    :param output_folder: 输出文件夹
    :param sensitivity: 敏感度 (0-1)。0.01 代表画面有 1% 的像素变动就提取。
                        对于文字提取，建议设置在 0.005 - 0.02 之间。
    :param min_interval: 最小时间间隔（秒）。防止动态效果（如鼠标移动）产生太多连拍。
    """
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("无法打开视频文件")
        return

    # 获取视频参数
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_pixels = width * height
    
    # 阈值：多少个像素变了才算变？
    change_threshold = total_pixels * sensitivity
    
    # 最小间隔帧数
    min_frame_interval = int(fps * min_interval)

    prev_saved_frame = None
    last_saved_frame_idx = -9999
    saved_count = 0

    print(f"开始分析: {video_path}")
    print(f"总帧数: {total_frames}, 敏感度阈值: {sensitivity} ({int(change_threshold)} 像素)")

    curr_frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 优化：跳过过密的帧（如果距离上一张保存的帧太近，直接跳过，提高速度）
        if (curr_frame_idx - last_saved_frame_idx) < min_frame_interval:
            curr_frame_idx += 1
            continue

        # 转为灰度图进行比较（减少计算量，且对文字对比度更敏感）
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 为了减少噪点（如视频压缩噪声），进行轻微的高斯模糊
        gray_frame = cv2.GaussianBlur(gray_frame, (5, 5), 0)

        should_save = False

        if prev_saved_frame is None:
            # 第一帧必存
            should_save = True
        else:
            # 计算当前帧和上一张“已保存帧”的差异
            # absdiff: 计算绝对差值
            diff = cv2.absdiff(prev_saved_frame, gray_frame)
            
            # 二值化：将微小的差异忽略，只保留明显的改变 (阈值 30 过滤掉噪点)
            _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
            
            # 计算非零像素点个数（即发生变化的面积）
            non_zero_count = cv2.countNonZero(thresh)
            
            # 核心判断：如果变化的像素数量超过阈值
            if non_zero_count > change_threshold:
                should_save = True
                # 可选：打印出变化的比例，方便调试
                # change_ratio = non_zero_count / total_pixels
                # print(f"帧 {curr_frame_idx} 变化率: {change_ratio:.4f} -> 保存")

        if should_save:
            # 保存图片
            filename = os.path.join(output_folder, f"slide_{saved_count:04d}_time_{curr_frame_idx/fps:.1f}s.jpg")
            cv2.imwrite(filename, frame) # 保存原色图
            
            saved_count += 1
            prev_saved_frame = gray_frame # 更新对比基准
            last_saved_frame_idx = curr_frame_idx
            print(f"\r已提取: {saved_count} 张 (当前进度: {curr_frame_idx}/{total_frames})", end="")

        curr_frame_idx += 1

    cap.release()
    print("\n完成！")

import subprocess
import os
import sys

def extract_frames_fast(video_path, output_folder):
    """
    使用 FFmpeg 从视频中提取关键帧 (I-frames)。
    
    :param video_path: 视频文件的路径 (例如: "input.mp4")
    :param output_folder: 保存图片的文件夹路径
    """
    
    # 1. 检查输入文件是否存在
    if not os.path.exists(video_path):
        print(f"错误: 找不到视频文件 '{video_path}'")
        return

    # 2. 如果输出目录不存在，则创建
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"已创建输出目录: {output_folder}")

    # 3. 构建 FFmpeg 命令
    # 核心参数解释:
    # -vf "select='eq(pict_type,I)'": 视频过滤器，只选择图片类型为 'I' (关键帧) 的帧
    # -vsync vfr: 可变帧率。丢弃未被选择的帧，防止 FFmpeg 复制帧来维持原始帧率
    # -q:v 2: 图片质量 (1-31, 1质量最高)。2 是非常好的质量
    
    output_pattern = os.path.join(output_folder, "keyframe_%03d.jpg")
    
    command = [
        'ffmpeg',
        '-i', video_path,                   # 输入文件
        '-vf', "select='eq(pict_type,I)'",  # 过滤器：只选关键帧
        '-vsync', 'vfr',                    # 丢弃非选定帧
        '-q:v', '2',                        # JPG 质量控制
        output_pattern                      # 输出文件模版
    ]

    print(f"正在开始提取关键帧，请稍候...")
    print(f"执行命令: {' '.join(command)}")

    try:
        # 4. 执行命令
        # capture_output=True 可以捕获日志，如果不需要看到详细刷屏可以保留
        result = subprocess.run(command, check=True, text=True, capture_output=False)
        print("-" * 30)
        print(f"成功！关键帧已提取到: {output_folder}")
        
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 执行出错: {e}")
    except FileNotFoundError:
        print("错误: 系统未找到 'ffmpeg' 命令。请确保已安装 FFmpeg 并配置了环境变量。")