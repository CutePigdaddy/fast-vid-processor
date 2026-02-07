#!/usr/bin/env python3
"""
AI转录文本分析支持模块 - 直接处理时间戳格式
功能：读取原始时间戳文本文件，直接发送给AI处理
"""

import os
import yaml
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from abc import ABC, abstractmethod

# ============================================================================
# 配置管理
# ============================================================================

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or self._find_config()
        self.config = self._load_config()
    
    def _find_config(self) -> str:
        """查找配置文件"""
        # 1. 检查当前目录
        current_dir = Path.cwd()
        config_path = current_dir / "config.yaml"
        if config_path.exists():
            return str(config_path)
        
        # 2. 检查模块所在目录
        module_dir = Path(__file__).parent
        config_path = module_dir / "config.yaml"
        if config_path.exists():
            return str(config_path)
        
        # 3. 创建默认配置
        default_config = self._create_default_config()
        config_path = module_dir / "config.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True)
        
        print(f"⚠️  未找到配置文件，已创建默认配置: {config_path}")
        return str(config_path)
    
    def _create_default_config(self) -> Dict[str, Any]:
        """创建默认配置"""
        return {
        'ai_service': {
            'provider': 'zhipu',  # 默认使用智谱AI
            'api_key': '${ZHIPU_API_KEY}',
            
            # OpenAI配置
            'openai': {
                'model': 'gpt-3.5-turbo',
                'temperature': 0.7,
                'max_tokens': 2000
            },
            
            # 智谱AI配置
            'zhipu': {
                'model': 'glm-4.7',
                'temperature': 1.0,
                'max_tokens': 2000,
                'top_p': 0.95,
                'incremental': False
            }
        },
            'summarization': {
                'output_dir': './summaries',
                'output_format': 'markdown',
                'language': 'zh'
            },
            'prompt_templates': {
                'timestamp_summary': '''你是一个专业的文本分析助手。请分析以下包含时间戳的转录文本内容：

{text_content}

重要说明：
1. 这是带有时间戳的转录文本，格式为：[开始时间 - 结束时间] 文本内容
2. 请忽略时间戳信息，专注于文本内容的分析和总结
3. 如果文本中有"## 完整文本"部分，请优先使用该部分内容
4. 如果有多人对话，请标注说话人

请按照以下结构组织分析和总结：
1. 内容概述,让用户对内容有一个整体把握
2. 时间线分析（按时间顺序梳理主要事件或观点）
3. 梳理整体的内容结构和行文逻辑
4. 选择几个关键的深刻洞见，进行分析和深入阐述
5. 总结与建议

语言：{language}''',
                'detailed_analysis': '''你是一个专业的文本分析助手。请对以下转录文本进行深入分析：

{text_content}

分析要求：
1. 忽略时间戳信息，专注于文本内容
2. 分析内容的结构和逻辑关系
3. 提取关键论点并进行逻辑梳理
4. 识别对话中的主要参与者和他们的观点
5. 评估内容的完整性和连贯性

分析维度：
1. 内容结构分析（开头、发展、结尾）
2. 主要观点与论据
3. 论证逻辑与说服力
4. 亮点与特色
5. 改进建议（如果有）

语言：{language}''',
                'quick_summary': '''请用简洁的语言总结以下转录文本：

{text_content}

要求：
1. 忽略时间戳信息
2. 字数在300字以内
3. 突出重点内容
4. 语言：{language}'''
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 处理环境变量
            config = self._replace_env_vars(config)
            return config
            
        except Exception as e:
            raise Exception(f"加载配置文件失败: {str(e)}")
    
    def _replace_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """替换环境变量"""
        def process_value(value):
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):

                env_var = value[2:-1]
                env_value = os.getenv(env_var, '')
                print(f"🔧 替换环境变量 {env_var} = {'***' if env_value else '空'}")
                return env_value
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process_value(v) for v in value]
            else:
                return value
        
        return process_value(config)
    
    def get_ai_config(self) -> Dict[str, Any]:
        """获取AI配置"""
        return self.config.get('ai_service', {})
    
    def get_prompt_templates(self) -> Dict[str, str]:
        """获取提示词模板"""
        return self.config.get('prompt_templates', {})


# ============================================================================
# AI客户端
# ============================================================================

class BaseAIClient(ABC):
    """AI客户端基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

class OpenAIClient(BaseAIClient):
    """OpenAI客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'gpt-3.5-turbo')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2000)
        
        if not self.api_key:
            raise ValueError("OpenAI API密钥未设置")
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("请安装openai库: pip install openai")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个专业的文本分析助手，擅长处理带有时间戳的转录文本。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=kwargs.get('temperature', self.temperature),
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                timeout=30
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"AI调用失败: {str(e)}")
        
# ============================================================================
# AI客户端 - 智谱AI支持
# ============================================================================

class ZhipuAIClient(BaseAIClient):
    """智谱AI客户端（使用新版zai-sdk）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'glm-4.7')  # 更新为最新模型
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2000)
        self.top_p = config.get('top_p', 0.7)
        self.incremental = config.get('incremental', False)
        
        if not self.api_key:
            raise ValueError("智谱AI API密钥未设置")
        
        try:
            from zai import ZhipuAiClient
            self.client = ZhipuAiClient(api_key=self.api_key)
        except ImportError:
            raise ImportError("请安装zai-sdk库: pip install zai-sdk")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        try:
            # 构建请求参数
            request_params = {
                "model": kwargs.get('model', self.model),
                "messages": [
                    {
                        "role": "system", 
                        "content": "你是一个专业的文本分析助手，擅长处理带有时间戳的转录文本。"
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get('temperature', self.temperature),
                "max_tokens": kwargs.get('max_tokens', self.max_tokens),
                "top_p": kwargs.get('top_p', self.top_p),
                "stream": kwargs.get('incremental', self.incremental),
            }
            
            # 调用智谱AI
            response = self.client.chat.completions.create(**request_params)
            
            # 处理响应
            if request_params.get('stream'):
                # 流式响应处理
                full_content = ""
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        full_content += chunk.choices[0].delta.content
                return full_content
            else:
                # 非流式响应处理
                return response.choices[0].message.content
                
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower():
                raise Exception(f"智谱AI额度不足或API密钥无效: {error_msg}")
            elif "rate limit" in error_msg.lower():
                raise Exception(f"智谱AI请求频率超限: {error_msg}")
            else:
                raise Exception(f"智谱AI调用失败: {error_msg}")


# ============================================================================
# 提示词管理器
# ============================================================================

class PromptManager:
    """提示词管理器"""
    
    def __init__(self, templates: Dict[str, str]):
        self.templates = templates
    
    def render(self, template_name: str, variables: Dict[str, Any]) -> str:
        """渲染提示词"""
        if template_name not in self.templates:
            # 使用默认提示词（专门处理时间戳格式）
            default_prompt = '''你是一个专业的文本分析助手。请分析以下转录文本：

{text_content}

重要说明：
1. 这是带有时间戳的转录文本，格式为：[开始时间 - 结束时间] 文本内容
2. 请忽略时间戳信息，专注于文本内容的分析和总结
3. 请按照以下结构组织：
   - 内容概述
   - 主要观点
   - 关键发现
   - 总结

语言：{language}'''
            
            template = default_prompt
        else:
            template = self.templates[template_name]
        
        # 替换变量
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            template = template.replace(placeholder, str(value))
        
        return template
    
    def list_templates(self) -> List[str]:
        """列出可用模板"""
        return list(self.templates.keys())


# ============================================================================
# 文件处理器
# ============================================================================

class TranscriptProcessor:
    """转录文本处理器（简化版）"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def get_content(self) -> str:
        """获取文件内容"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                raise ValueError("文件内容为空")
            
            return content
            
        except Exception as e:
            raise Exception(f"读取文件失败: {str(e)}")
    
    def get_metadata(self) -> Dict[str, str]:
        """获取文件元数据"""
        return {
            'file_name': Path(self.file_path).name,
            'file_size': os.path.getsize(self.file_path),
            'process_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


# ============================================================================
# 总结生成器
# ============================================================================

class SummaryGenerator:
    """总结生成器"""
    
    def __init__(self, ai_client: BaseAIClient, prompt_manager: PromptManager, config: Dict[str, Any]):
        self.ai_client = ai_client
        self.prompt_manager = prompt_manager
        self.config = config
        self.language = config.get('language', 'zh')
    
    def generate(self, text: str, template_name: str = "timestamp_summary", 
                custom_vars: Dict[str, Any] = None) -> str:
        """生成总结"""
        
        # 准备变量
        variables = {
            'text_content': text,
            'language': self.language,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'text_length': len(text)
        }
        
        if custom_vars:
            variables.update(custom_vars)
        
        # 渲染提示词
        prompt = self.prompt_manager.render(template_name, variables)
        
        print(f"🧠 正在调用AI处理时间戳文本...")
        print(f"  文本长度: {len(text):,} 字符")
        print(f"  使用模板: {template_name}")
        
        try:
            summary = self.ai_client.generate(prompt)
            
            print(f"✅ AI处理完成")
            print(f"📄 总结长度: {len(summary):,} 字符")
            
            return summary
            
        except Exception as e:
            raise Exception(f"生成总结失败: {str(e)}")


# ============================================================================
# 输出处理器
# ============================================================================

class OutputHandler:
    """输出处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = config.get('output_dir', './summaries')
        self.output_format = config.get('output_format', 'markdown')
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
    
    def save(self, summary: str, metadata: Dict[str, Any], 
            source_file: str, template_used: str, ai_model: str) -> str:
        """保存总结"""
        
        # 生成文件名
        source_name = Path(source_file).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_summary_{timestamp}"
        
        # 根据格式保存
        if self.output_format == 'json':
            filepath = self._save_json(filename, summary, metadata, source_file, template_used, ai_model)
        else:  # 默认markdown
            filepath = self._save_markdown(filename, summary, metadata, source_file, template_used, ai_model)
        
        return filepath
    
    def _save_markdown(self, filename: str, summary: str, metadata: Dict[str, Any],
                      source_file: str, template_used: str, ai_model: str) -> str:
        """保存为Markdown"""
        filepath = os.path.join(self.output_dir, f"{filename}.md")
        
        content = f"""# 📝 转录文本分析总结

## 📋 分析信息
- **源文件**: `{source_file}`
- **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **AI模型**: {ai_model}
- **分析模板**: {template_used}
- **文件大小**: {metadata['file_size']:,} 字节

## 💡 重要说明
此分析基于原始时间戳格式的转录文本，AI已按照指令处理时间戳信息并提取核心内容。

---

## 📈 AI分析总结

{summary}

---

<div align="center">
<small>✨ 由 AI转录文本分析系统 生成 | 处理时间: {metadata['process_time']} ✨</small>
</div>"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _save_json(self, filename: str, summary: str, metadata: Dict[str, Any],
                  source_file: str, template_used: str, ai_model: str) -> str:
        """保存为JSON"""
        filepath = os.path.join(self.output_dir, f"{filename}.json")
        
        data = {
            "summary": summary,
            "metadata": {
                "source_file": source_file,
                "generated_at": datetime.now().isoformat(),
                "ai_model": ai_model,
                "template_used": template_used,
                **metadata
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath


# ============================================================================
# 主控制器
# ============================================================================

class AISupport:
    """AI支持主控制器"""
    
    def __init__(self, config_path: str = None):
        """初始化"""
        print("🚀 初始化AI转录文本分析系统...")
        
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config
        self.ai_config = self.config_manager.get_ai_config()
        self.prompt_templates = self.config_manager.get_prompt_templates()
        
        # 初始化组件
        self.prompt_manager = PromptManager(self.prompt_templates)
        self.ai_client = self._create_ai_client()
        self.summary_generator = SummaryGenerator(
            self.ai_client, 
            self.prompt_manager, 
            self.config.get('summarization', {})
        )
        self.output_handler = OutputHandler(
            self.config.get('summarization', {})
        )
        
        print(f"✅ 系统初始化完成")
        print(f"   AI服务: {self.ai_config.get('provider', '未配置')}")
        print(f"   输出目录: {self.config.get('summarization', {}).get('output_dir', './summaries')}")
    
    def _create_ai_client(self) -> BaseAIClient:
        """创建AI客户端"""
        provider = self.ai_config.get('provider', 'zhipu').lower()

        if provider == 'openai':
            api_key = self.ai_config.get('api_key')
            if not api_key:
                # 检查是否有openai子配置
                openai_config = self.ai_config.get('openai', {})
                api_key = openai_config.get('api_key')

            if not api_key:
                raise ValueError("OpenAI API密钥未配置。请设置环境变量: export OPENAI_API_KEY=your_key")

            # 合并配置
            openai_config = self.ai_config.get('openai', {}).copy()
            openai_config['api_key'] = api_key

            return OpenAIClient(openai_config)

        elif provider == 'zhipu':
            api_key = self.ai_config.get('api_key')
            if not api_key:
                # 检查是否有zhipu子配置
                zhipu_config = self.ai_config.get('zhipu', {})
                api_key = zhipu_config.get('api_key')

            if not api_key:
                raise ValueError("智谱AI API密钥未配置。请设置环境变量: export ZHIPU_API_KEY=your_key")

            # 合并配置
            zhipu_config = self.ai_config.get('zhipu', {}).copy()
            zhipu_config['api_key'] = api_key

            return ZhipuAIClient(zhipu_config)

        else:
            raise ValueError(f"不支持的AI服务商: {provider}。支持的服务商: openai, zhipu")
    
    def analyze_file(self, file_path: str, template_name: str = "timestamp_summary", 
                    output_format: str = None) -> Dict[str, Any]:
        """分析文件"""
        
        print(f"\n📂 开始分析文件: {file_path}")
        
        # 验证文件
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取文件内容（保持原始格式，包括时间戳）
        processor = TranscriptProcessor(file_path)
        file_content = processor.get_content()
        metadata = processor.get_metadata()
        
        if not file_content.strip():
            raise ValueError("文件内容为空")
        
        print(f"📄 读取文件成功，长度: {len(file_content):,} 字符")
        
        # 生成总结
        try:
            summary = self.summary_generator.generate(file_content, template_name)
        except Exception as e:
            print(f"❌ 生成总结失败: {str(e)}")
            raise
        
        # 保存结果
        ai_model = self.ai_config.get('model', 'unknown')
        if output_format:
            # 临时修改输出格式
            temp_config = self.config.get('summarization', {}).copy()
            temp_config['output_format'] = output_format
            temp_handler = OutputHandler(temp_config)
            output_file = temp_handler.save(summary, metadata, file_path, template_name, ai_model)
        else:
            output_file = self.output_handler.save(summary, metadata, file_path, template_name, ai_model)
        
        # 返回结果
        result = {
            'success': True,
            'input_file': file_path,
            'output_file': output_file,
            'text_length': len(file_content),
            'summary_length': len(summary),
            'template_used': template_name,
            'ai_model': ai_model,
            'metadata': metadata
        }
        
        print(f"\n🎉 分析完成!")
        print(f"   📍 输出文件: {output_file}")
        print(f"   📊 原始文本: {len(file_content):,} 字符")
        print(f"   📝 AI总结: {len(summary):,} 字符")
        
        return result
    
    def list_templates(self) -> List[str]:
        """列出可用模板"""
        return self.prompt_manager.list_templates()
    
    def show_config(self) -> Dict[str, Any]:
        """显示配置信息"""
        return {
            'config_path': self.config_manager.config_path,
            'ai_service': self.ai_config,
            'summarization': self.config.get('summarization', {}),
            'available_templates': self.list_templates()
        }


# ============================================================================
# 命令行接口
# ============================================================================

def main():
    """命令行入口"""
    
    parser = argparse.ArgumentParser(
        description='AI转录文本分析系统 - 直接处理时间戳格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s input.txt                    # 基本使用（使用时间戳模板）
  %(prog)s input.txt --template detailed_analysis  # 详细分析
  %(prog)s input.txt --format json      # 输出JSON格式
  %(prog)s --list-templates             # 列出可用模板
  %(prog)s --show-config                # 显示配置信息

注意：
  系统直接将原始文件内容（包括时间戳）发送给AI处理
  请确保AI模型能够处理文件长度（可能超过token限制）
        """
    )
    
    parser.add_argument('input_file', nargs='?', help='输入文件路径')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--template', '-t', default='timestamp_summary', 
                       help='提示词模板名称 (默认: timestamp_summary)')
    parser.add_argument('--format', '-f', choices=['markdown', 'json'], 
                       help='输出格式 (默认从配置读取)')
    parser.add_argument('--list-templates', action='store_true', 
                       help='列出可用模板')
    parser.add_argument('--show-config', action='store_true', 
                       help='显示配置信息')
    parser.add_argument('--output-dir', '-o', help='输出目录')
    
    args = parser.parse_args()
    
    try:
        # 创建实例
        ai_support = AISupport(args.config)
        
        # 处理特殊命令
        if args.list_templates:
            templates = ai_support.list_templates()
            print("\n📋 可用模板:")
            for template in templates:
                print(f"  - {template}")
            return
        
        if args.show_config:
            config_info = ai_support.show_config()
            print("\n⚙️  配置信息:")
            print(yaml.dump(config_info, allow_unicode=True, default_flow_style=False))
            return
        
        # 检查输入文件
        if not args.input_file:
            print("❌ 错误: 请指定输入文件")
            parser.print_help()
            return
        
        # 分析文件
        result = ai_support.analyze_file(
            file_path=args.input_file,
            template_name=args.template,
            output_format=args.format
        )
        
        # 显示总结预览
        if result['success']:
            print("\n📋 总结预览:")
            print("=" * 60)
            
            # 读取并显示部分总结
            with open(result['output_file'], 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 显示前20行
            lines = content.split('\n')
            for i, line in enumerate(lines[:20]):
                if i >= 20:
                    print("...")
                    break
                print(line)
            
            print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        return 1
    
    return 0


# ============================================================================
# 导入接口
# ============================================================================

def analyze_transcript(file_path: str, template: str = "timestamp_summary", 
                      config_path: str = None) -> Dict[str, Any]:
    """
    分析转录文本的主函数
    
    参数:
        file_path: 输入文件路径
        template: 提示词模板名称
        config_path: 配置文件路径
    
    返回:
        包含分析结果的字典
    """
    ai_support = AISupport(config_path)
    return ai_support.analyze_file(file_path, template)


def get_available_templates(config_path: str = None) -> List[str]:
    """获取可用模板列表"""
    ai_support = AISupport(config_path)
    return ai_support.list_templates()


# ============================================================================
# 直接运行
# ============================================================================

if __name__ == "__main__":
    exit(main())