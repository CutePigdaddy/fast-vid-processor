from .separator import Separator 
from .distract import distractor
from .compress import compresser
'''
需要有pytorch cuda 同时安装onnxruntime-gpu才可以调用gpu加速
这个模块中的所有函数/对象最好全部显式指定路径
使用示例:
在main(外部文件中):
from modules.track import compresser, Separator, distractor
然后调用:
compresser(输入路径, 输出路径)  这个是压缩
separator = Separator()     这个是分离音轨对象的初始化
separator.extract_audio(输入路径, 输出路径) 这个是分离出人声音轨
distractor(输入路径, 输出路径)  这个是去伴奏
'''