from modules.vision import extract_frames

if __name__ == "__main__":
    """
    关键帧提取示例
    By YBJ
    """
    video_file = "example.mp4" # 视频链接
    output_dir = "text_keyframes"
    
    # sensitivity=0.005 代表 0.5% 的区域变化就触发
    # 对于 PPT 翻页，0.01 (1%) 比较合适
    # 对于 字幕变化，0.005 (0.5%) 比较合适
    extract_frames(video_file, output_dir, sensitivity=0.005, min_interval=1.0)