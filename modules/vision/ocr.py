from paddleocr import PaddleOCR

def perform_ocr(input_image_path: str, output_folder: str):
    # 初始化 PaddleOCR，禁用不需要的模型以提升速度
    ocr = PaddleOCR(
        use_doc_orientation_classify=False, # 通过 use_doc_orientation_classify 参数指定不使用文档方向分类模型
        use_doc_unwarping=False, # 通过 use_doc_unwarping 参数指定不使用文本图像矫正模型
        use_textline_orientation=False, # 通过 use_textline_orientation 参数指定不使用文本行方向分类模型
    )
    result = ocr.predict(input_image_path)
    for res in result:
        res.print()
        # 保存效果对比图
        # res.save_to_img(output_folder)
        res.save_to_json(output_folder)