# AI 转录文本分析支持模块

## 1. 模块概述

AI 转录文本分析支持模块是一个专门用于处理带有时间戳的转录文本的智能分析系统。该模块能够直接读取原始时间戳格式的文本文件，通过 AI 模型进行分析和总结，生成结构化的分析报告。

### 1.1 核心功能

- **直接处理时间戳格式**：无需预处理，直接读取和分析带有时间戳的转录文本
- **多 AI 服务支持**：支持智谱AI (GLM-4.7) 和 OpenAI (GPT-3.5-turbo) 模型
- **多种分析模板**：提供时间戳总结、详细分析和快速总结等多种分析模板
- **多格式输出**：支持 Markdown 和 JSON 格式的分析结果
- **智能配置管理**：自动配置和环境变量支持，使用方便
- **详细的错误处理**：提供清晰的错误信息和异常处理
- **美观的输出格式**：生成结构清晰、美观易读的分析报告

## 2. 目录结构

```
ai_support/
├── ai_support.py      # 核心功能模块
├── config.yaml        # 配置文件
├── README.md          # 说明文档
└── __pycache__/       # 编译缓存
```

## 3. 安装与配置

### 3.1 依赖安装

该模块依赖以下 Python 包：

- **yaml**：用于解析配置文件
- **zai-sdk**：用于调用智谱AI API（使用智谱AI时需要）
- **openai**：用于调用 OpenAI API（使用 OpenAI 时需要）

安装依赖：

```bash
# 安装基本依赖
pip install pyyaml

# 安装智谱AI SDK（使用智谱AI时需要）
pip install zai-sdk

# 安装 OpenAI SDK（使用 OpenAI 时需要）
pip install openai
```

### 3.2 API 密钥配置

该模块支持从环境变量加载 API 密钥，推荐使用这种方式：

#### 3.2.1 Windows CMD

```cmd
# 设置智谱AI API密钥
set ZHIPU_API_KEY=your_api_key

# 设置 OpenAI API密钥
set OPENAI_API_KEY=your_api_key
```

#### 3.2.2 Windows PowerShell

```powershell
# 设置智谱AI API密钥
$env:ZHIPU_API_KEY="your_api_key"

# 设置 OpenAI API密钥
$env:OPENAI_API_KEY="your_api_key"
```

#### 3.2.3 Linux/Mac

```bash
# 设置智谱AI API密钥
export ZHIPU_API_KEY=your_api_key

# 设置 OpenAI API密钥
export OPENAI_API_KEY=your_api_key
```

### 3.3 配置文件

模块会自动创建默认配置文件 `config.yaml`，您可以根据需要修改：

```yaml
ai_service:
  provider: zhipu  # 默认使用智谱AI
  api_key: ${ZHIPU_API_KEY}
  
  # OpenAI配置
  openai:
    model: gpt-3.5-turbo
    temperature: 0.7
    max_tokens: 2000
  
  # 智谱AI配置
  zhipu:
    model: glm-4.7
    temperature: 1.0
    max_tokens: 2000
    top_p: 0.95
    incremental: False
summarization:
  output_dir: ./summaries
  output_format: markdown
  language: zh
prompt_templates:
  timestamp_summary: '''你是一个专业的文本分析助手。请分析以下包含时间戳的转录文本内容：

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

语言：{language}'''
  detailed_analysis: '''你是一个专业的文本分析助手。请对以下转录文本进行深入分析：

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

语言：{language}'''
  quick_summary: '''请用简洁的语言总结以下转录文本：

{text_content}

要求：
1. 忽略时间戳信息
2. 字数在300字以内
3. 突出重点内容
4. 语言：{language}'''
```

## 4. 使用方法

### 4.1 命令行使用

该模块提供了方便的命令行接口，可以直接分析文本文件：

#### 4.1.1 基本使用

```bash
# 基本分析（使用时间戳模板）
python -m ai_support input.txt

# 详细分析
python -m ai_support input.txt --template detailed_analysis

# 快速总结
python -m ai_support input.txt --template quick_summary

# 输出 JSON 格式
python -m ai_support input.txt --format json

# 指定输出目录
python -m ai_support input.txt --output-dir ./my_summaries
```

#### 4.1.2 特殊命令

```bash
# 列出可用模板
python -m ai_support --list-templates

# 显示配置信息
python -m ai_support --show-config
```

### 4.2 代码集成

该模块提供了简洁的导入接口，可以在其他 Python 代码中使用：

#### 4.2.1 分析转录文本

```python
from ai_support import analyze_transcript

result = analyze_transcript(
    file_path="input.txt",
    template="timestamp_summary",
    config_path="config.yaml"
)

print(f"分析成功: {result['success']}")
print(f"输出文件: {result['output_file']}")
print(f"文本长度: {result['text_length']} 字符")
print(f"总结长度: {result['summary_length']} 字符")
```

#### 4.2.2 获取可用模板

```python
from ai_support import get_available_templates

templates = get_available_templates()
print("可用模板:", templates)
```

## 5. 核心功能详细说明

### 5.1 配置管理

配置管理器 (`ConfigManager`) 负责加载和管理系统配置：

- **自动配置**：当配置文件不存在时，自动创建默认配置
- **环境变量支持**：从环境变量加载 API 密钥，提高安全性
- **配置验证**：确保必要的配置项存在，提供合理的默认值

### 5.2 AI 客户端

系统支持多种 AI 服务提供商：

- **智谱AI客户端**：使用新版 zai-sdk，支持 GLM-4.7 模型
- **OpenAI客户端**：支持 GPT-3.5-turbo 模型
- **统一接口**：提供一致的 `generate` 方法，简化调用
- **错误处理**：详细的错误信息和异常处理，便于调试

### 5.3 提示词管理

提示词管理器 (`PromptManager`) 负责构建和管理 AI 提示词：

- **模板系统**：支持多种分析模板（时间戳总结、详细分析、快速总结）
- **变量替换**：动态替换提示词中的变量（如文本内容、语言设置）
- **默认模板**：当指定模板不存在时使用默认模板，提高系统鲁棒性

### 5.4 文本处理

转录文本处理器 (`TranscriptProcessor`) 负责读取和处理转录文本：

- **文件读取**：读取转录文本文件内容
- **元数据提取**：提取文件元数据（文件名、大小、处理时间）
- **原始格式**：保持原始格式，包括时间戳信息

### 5.5 总结生成

总结生成器 (`SummaryGenerator`) 负责调用 AI 模型生成分析总结：

- **AI 调用**：调用 AI 模型生成分析总结
- **模板渲染**：根据选择的模板渲染提示词
- **进度反馈**：提供详细的处理进度和信息

### 5.6 输出处理

输出处理器 (`OutputHandler`) 负责处理和保存分析结果：

- **格式支持**：支持 Markdown 和 JSON 格式
- **目录管理**：自动创建输出目录
- **元数据保存**：保存分析过程的元数据信息
- **美观格式**：Markdown 输出带有美观的格式和信息

## 6. 分析模板说明

### 6.1 时间戳总结 (timestamp_summary)

- **用途**：专门用于分析带有时间戳的转录文本
- **分析结构**：
  1. 内容概述：整体把握内容
  2. 时间线分析：按时间顺序梳理主要事件或观点
  3. 内容结构和逻辑：梳理整体结构和行文逻辑
  4. 关键洞见：选择几个关键洞见进行深入分析
  5. 总结与建议：提供总结和建议
- **特点**：忽略时间戳信息，专注于内容分析


## 7. 输出格式说明

### 7.1 Markdown 格式

Markdown 格式的输出文件包含以下内容：

- **分析信息**：源文件、生成时间、AI 模型、分析模板等
- **重要说明**：关于分析过程的重要说明
- **AI 分析总结**：AI 生成的分析总结内容
- **生成信息**：处理时间等元数据

### 7.2 JSON 格式

JSON 格式的输出文件包含以下内容：

- **summary**：AI 生成的分析总结内容
- **metadata**：包含源文件、生成时间、AI 模型、分析模板等元数据

## 8. 配置选项

### 8.1 AI 服务配置

| 配置项 | 说明 | 默认值 |
|-------|------|-------|
| provider | AI 服务提供商（zhipu 或 openai） | zhipu |
| api_key | API 密钥 | ${ZHIPU_API_KEY}（从环境变量读取） |
| openai.model | OpenAI 模型名称 | gpt-3.5-turbo |
| openai.temperature | OpenAI 温度参数 | 0.7 |
| openai.max_tokens | OpenAI 最大 tokens | 2000 |
| zhipu.model | 智谱AI 模型名称 | glm-4.7 |
| zhipu.temperature | 智谱AI 温度参数 | 1.0 |
| zhipu.max_tokens | 智谱AI 最大 tokens | 2000 |
| zhipu.top_p | 智谱AI top_p 参数 | 0.95 |
| zhipu.incremental | 智谱AI 是否使用流式响应 | False |

### 8.2 总结配置

| 配置项 | 说明 | 默认值 |
|-------|------|-------|
| output_dir | 输出目录 | ./summaries |
| output_format | 输出格式（markdown 或 json） | markdown |
| language | 分析语言 | zh |

## 9. 常见问题与故障排除

### 9.1 API 密钥问题

**问题**：`智谱AI API密钥未设置` 或 `OpenAI API密钥未配置`

**解决方案**：
1. 确保已正确设置环境变量：
   - Windows CMD: `set ZHIPU_API_KEY=your_api_key`
   - Windows PowerShell: `$env:ZHIPU_API_KEY="your_api_key"`
   - Linux/Mac: `export ZHIPU_API_KEY=your_api_key`
2. 或在配置文件中直接设置 API 密钥（不推荐，安全性较低）

### 9.2 依赖问题

**问题**：`ImportError: 请安装zai-sdk库: pip install zai-sdk` 或 `ImportError: 请安装openai库: pip install openai`

**解决方案**：
1. 安装缺少的依赖：
   - 智谱AI: `pip install zai-sdk`
   - OpenAI: `pip install openai`

### 9.3 文件问题

**问题**：`读取文件失败: [Errno 2] No such file or directory: 'input.txt'` 或 `文件内容为空`

**解决方案**：
1. 确保输入文件路径正确
2. 确保输入文件不为空，包含有效的转录文本

### 9.4 AI 调用问题

**问题**：`智谱AI调用失败: ...` 或 `AI调用失败: ...`

**解决方案**：
1. 检查 API 密钥是否有效
2. 检查网络连接是否正常
3. 检查 AI 服务是否正常运行
4. 尝试减少输入文本长度，避免超过模型的 token 限制

- **当前版本**：1.0.0
- **最后更新**：2026-02-10
- **支持的 Python 版本**：3.7+
