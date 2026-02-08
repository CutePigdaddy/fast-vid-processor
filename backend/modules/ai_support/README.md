# AI Support 模块

AI Support 是一个专业的转录文本分析系统，专为处理带有时间戳的转录文本设计，利用 AI 技术生成高质量的分析总结。

## 功能特点

### 核心功能
- **智能文本分析**：利用 AI 模型分析转录文本内容
- **多种分析模板**：支持时间戳总结、详细分析、快速总结和对话分析
- **多 AI 服务支持**：集成智谱AI和OpenAI
- **自动配置管理**：智能查找和加载配置文件
- **丰富的输出格式**：支持 Markdown 和 JSON 输出
- **命令行接口**：提供便捷的命令行操作

### 技术特点
- **模块化设计**：清晰的组件划分，易于扩展
- **灵活配置**：支持环境变量和配置文件
- **用户友好**：详细的日志和错误提示
- **性能优化**：合理的错误处理和资源管理

## 目录结构

```
ai_support/
├── ai_support.py       # 主模块文件
├── config.yaml         # 配置文件
└── README.md           # 本文档
```

## 快速开始

### 安装依赖

```bash
# 使用虚拟环境
.venv\Scripts\pip.exe install pyyaml zai-sdk openai sniffio

# 或直接安装
pip install pyyaml zai-sdk openai sniffio
```

### 设置 API 密钥

#### 智谱AI
设置环境变量 `ZHIPU_API_KEY`：

```cmd
# 临时设置（仅当前会话）
set ZHIPU_API_KEY=your_api_key

# 永久设置（系统级别）
# 右键点击"此电脑" → 属性 → 高级系统设置 → 环境变量
```

#### OpenAI
设置环境变量 `OPENAI_API_KEY`：

```cmd
set OPENAI_API_KEY=your_api_key
```

### 基本使用

#### 命令行使用

```bash
# 分析转录文件
python ai_support.py input.txt

# 使用详细分析模板
python ai_support.py input.txt --template detailed_analysis

# 输出 JSON 格式
python ai_support.py input.txt --format json

# 列出可用模板
python ai_support.py --list-templates

# 显示配置信息
python ai_support.py --show-config
```

#### 代码集成

```python
from ai_support.ai_support import analyze_transcript

# 分析转录文本
result = analyze_transcript('path/to/transcript.txt')

# 查看结果
print(f"总结文件: {result['output_file']}")
print(f"总结长度: {result['summary_length']} 字符")
```

## 配置选项

### 配置文件

配置文件 `config.yaml` 包含以下选项：

```yaml
# AI服务配置
ai_service:
  provider: "zhipu"  # 可选: openai, zhipu
  api_key: "${ZHIPU_API_KEY}"  # 从环境变量读取
  
  # OpenAI配置
  openai:
    model: "gpt-3.5-turbo"
    temperature: 0.7
    max_tokens: 2000
  
  # 智谱AI配置
  zhipu:
    model: "glm-4"  # 可选: glm-4, glm-4.7
    temperature: 0.7
    max_tokens: 2000
    top_p: 0.7
    incremental: false

# 总结配置
summarization:
  output_dir: "./summaries"
  output_format: "markdown"
  language: "zh"

# 提示词模板
prompt_templates:
  timestamp_summary: |
    # 时间戳总结模板
    # ...
  detailed_analysis: |
    # 详细分析模板
    # ...
  quick_summary: |
    # 快速总结模板
    # ...
  conversation_analysis: |
    # 对话分析模板
    # ...
```

### 环境变量

| 环境变量 | 描述 |
|----------|------|
| `ZHIPU_API_KEY` | 智谱AI API密钥 |
| `OPENAI_API_KEY` | OpenAI API密钥 |

## 分析模板

### 1. timestamp_summary
适合带有时间戳的转录文本，提供结构化的分析和总结：
- 内容概述
- 时间线分析
- 核心观点提取
- 关键洞见
- 总结与建议

### 2. detailed_analysis
提供更深入的文本分析：
- 内容结构分析
- 主要观点与论据
- 论证逻辑与说服力
- 亮点与特色
- 改进建议

### 3. quick_summary
生成简洁的文本摘要（300字以内）：
- 突出重点内容
- 忽略时间戳信息
- 语言简洁明了

### 4. conversation_analysis
专门用于对话转录的分析：
- 对话参与者识别
- 对话结构分析
- 参与者观点提取
- 共识和分歧点分析
- 对话效果评估

## 输出格式

### Markdown 输出

生成的 Markdown 文件包含：
- 分析信息（源文件、生成时间、AI模型等）
- 重要说明
- AI 分析总结（结构化内容）
- 生成信息

### JSON 输出

生成的 JSON 文件包含：
- 总结内容
- 元数据（源文件、生成时间、AI模型等）
- 处理信息

## 集成到其他系统

### 与音频转录系统集成

AI Support 模块可以轻松集成到音频转录系统中，实现转录后自动分析：

```python
from ai_support.ai_support import analyze_transcript

# 处理音频后调用
def process_audio(audio_path):
    # 1. 转录音频
    transcript_file = transcribe_audio(audio_path)
    
    # 2. 分析转录文本
    summary_result = analyze_transcript(transcript_file)
    
    return summary_result
```

## 常见问题

### Q: API 密钥如何设置？
A: 设置环境变量 `ZHIPU_API_KEY`（智谱AI）或 `OPENAI_API_KEY`（OpenAI）。

### Q: 支持哪些 AI 模型？
A: 智谱AI支持 `glm-4`、`glm-4.7` 等模型；OpenAI支持 `gpt-3.5-turbo`、`gpt-4` 等模型。

### Q: 如何自定义分析模板？
A: 修改 `config.yaml` 文件中的 `prompt_templates` 部分。

### Q: 输出文件保存在哪里？
A: 默认保存在 `./summaries` 目录，可在配置文件中修改。

### Q: 如何处理大型文件？
A: 对于大型文件，建议使用 `quick_summary` 模板，或增加模型的 `max_tokens` 设置。

## 性能优化

### 提高分析速度
- 使用更强大的 AI 模型
- 增加 `max_tokens` 设置
- 对于大型文件，使用 `quick_summary` 模板

### 提高分析质量
- 使用 `detailed_analysis` 模板
- 调整 `temperature` 参数（较低的值更保守，较高的值更有创造性）
- 确保输入文本质量良好

## 故障排除

### 常见错误

| 错误信息 | 可能原因 | 解决方案 |
|----------|----------|----------|
| API密钥未配置 | 环境变量未设置 | 设置对应的环境变量 |
| 模块导入失败 | 依赖未安装 | 安装缺少的依赖包 |
| 配置文件未找到 | 路径错误 | 确保配置文件存在或使用默认配置 |
| 模型调用失败 | 网络问题或API限制 | 检查网络连接或API配额 |

### 日志查看

系统会生成详细的日志，帮助排查问题：
- 初始化信息
- 配置加载情况
- AI 调用状态
- 错误信息

## 版本历史

### v1.0.0
- 初始版本
- 支持智谱AI和OpenAI
- 提供多种分析模板
- 支持 Markdown 和 JSON 输出

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 联系信息

如有问题或建议，请通过以下方式联系：
- 项目维护者：[Your Name]
- 邮箱：[your.email@example.com]

---

**✨ 由 AI Support 团队开发**
