# Agent Template Parser 故障排除指南

本指南帮助您诊断和解决使用 Agent Template Parser 时遇到的常见问题。

## 目录

1. [安装和环境问题](#安装和环境问题)
2. [模板解析错误](#模板解析错误)
3. [配置生成问题](#配置生成问题)
4. [批量处理错误](#批量处理错误)
5. [LLM 增强问题](#llm-增强问题)
6. [文件操作错误](#文件操作错误)
7. [性能问题](#性能问题)
8. [调试工具](#调试工具)

## 安装和环境问题

### 问题 1: 导入模块失败

**错误信息**:
```
ModuleNotFoundError: No module named 'src.agent_template_parser'
```

**原因**: Python 路径配置问题或依赖未安装

**解决方案**:
```bash
# 1. 确保在项目根目录
pwd  # 应该显示项目根目录路径

# 2. 检查 Python 路径
python -c "import sys; print('\n'.join(sys.path))"

# 3. 安装依赖
pip install -r requirements.txt

# 4. 如果仍有问题，尝试设置 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 问题 2: 依赖版本冲突

**错误信息**:
```
ERROR: pip's dependency resolver does not currently consider all the packages that are installed
```

**解决方案**:
```bash
# 1. 创建虚拟环境
python -m venv agent_parser_env
source agent_parser_env/bin/activate  # Linux/Mac
# 或
agent_parser_env\Scripts\activate  # Windows

# 2. 升级 pip
pip install --upgrade pip

# 3. 安装依赖
pip install -r requirements.txt
```

## 模板解析错误

### 问题 1: 系统提示词解析失败

**错误信息**:
```
TemplateParsingError: System prompt parsing failed: System prompt content cannot be empty
```

**原因**: 模板文件为空或编码问题

**解决方案**:
```bash
# 1. 检查文件是否存在且不为空
ls -la templates/system_prompts/your_agent_system.txt
wc -l templates/system_prompts/your_agent_system.txt

# 2. 检查文件编码
file templates/system_prompts/your_agent_system.txt

# 3. 转换编码（如果需要）
iconv -f GBK -t UTF-8 input.txt > output.txt
```

**Python 调试**:
```python
# 检查文件内容
with open('templates/system_prompts/your_agent_system.txt', 'r', encoding='utf-8') as f:
    content = f.read()
    print(f"文件长度: {len(content)}")
    print(f"前100字符: {content[:100]}")
```

### 问题 2: JSON 测试用例解析失败

**错误信息**:
```
TemplateParsingError: Invalid JSON in test case: Expecting ',' delimiter: line 5 column 10 (char 89)
```

**原因**: JSON 格式错误

**解决方案**:
```bash
# 1. 使用 JSON 验证工具
python -m json.tool templates/test_cases/your_agent_test.json

# 2. 或使用在线 JSON 验证器
# https://jsonlint.com/
```

**常见 JSON 错误**:
```json
// ❌ 错误：多余的逗号
{
  "field1": "value1",
  "field2": "value2",  // <- 多余的逗号
}

// ✅ 正确
{
  "field1": "value1",
  "field2": "value2"
}

// ❌ 错误：单引号
{
  'field': 'value'  // <- 应该使用双引号
}

// ✅ 正确
{
  "field": "value"
}
```

### 问题 3: 变量提取不正确

**错误信息**:
```
No variables found in template
```

**原因**: 变量格式不正确或不被识别

**解决方案**:
```python
# 检查变量格式
from src.agent_template_parser import TemplateParser

parser = TemplateParser()
content = "你的模板内容 ${sys.user_input} {user}"

# 测试变量提取
variables = parser.extract_variables(content)
print("提取的变量:", variables)

# 支持的变量格式：
# ${sys.user_input} - 系统变量
# {user} - 简单变量
# {role} - 简单变量
```

## 配置生成问题

### 问题 1: Agent 配置生成失败

**错误信息**:
```
ConfigGenerationError: Agent configuration generation failed: 'dict' object has no attribute 'get_all_variables'
```

**原因**: 传递给配置生成器的数据格式不正确

**解决方案**:
```python
from src.agent_template_parser import TemplateParser, AgentConfigGenerator
from src.agent_template_parser.models import ParsedTemplate

# ❌ 错误的用法
config_generator = AgentConfigGenerator()
agent_config = config_generator.generate_agent_yaml(
    {"some": "dict"},  # 错误：应该传递 ParsedTemplate 对象
    "agent_name"
)

# ✅ 正确的用法
parser = TemplateParser()
system_data = parser.parse_system_prompt(system_prompt)
user_data = parser.parse_user_input(user_input)
test_data = parser.parse_test_case(test_case)

parsed_template = parser.create_parsed_template(system_data, user_data, test_data)
agent_config = config_generator.generate_agent_yaml(parsed_template, "agent_name")
```

### 问题 2: 配置文件保存失败

**错误信息**:
```
ConfigGenerationError: Configuration file saving failed: unsupported operand type(s) for /: 'str' and 'str'
```

**原因**: 路径配置问题

**解决方案**:
```python
from pathlib import Path

# ❌ 错误：agents_dir 是字符串
config_generator.agents_dir = "agents"

# ✅ 正确：agents_dir 应该是 Path 对象
config_generator.agents_dir = Path("agents")

# 或者在初始化时指定
config_generator = AgentConfigGenerator("agents")  # 这会自动转换为 Path
```

### 问题 3: 生成的配置格式不正确

**错误信息**:
```
yaml.constructor.ConstructorError: could not determine a constructor for the tag
```

**原因**: 配置中包含不支持的数据类型

**解决方案**:
```python
import yaml

# 检查配置内容
with open('agents/your_agent/agent.yaml', 'r') as f:
    try:
        config = yaml.safe_load(f)
        print("配置加载成功")
    except yaml.YAMLError as e:
        print(f"YAML 格式错误: {e}")

# 验证配置结构
expected_keys = ['id', 'name', 'flows', 'evaluation', 'case_fields']
missing_keys = [key for key in expected_keys if key not in config]
if missing_keys:
    print(f"缺少必需字段: {missing_keys}")
```

## 批量处理错误

### 问题 1: 目标 Agent 不存在

**错误信息**:
```
BatchProcessingError: Target agent 'your_agent' does not exist
```

**原因**: 指定的 agent 不存在或路径不正确

**解决方案**:
```bash
# 1. 检查 agent 是否存在
ls -la agents/your_agent/
ls -la agents/your_agent/agent.yaml

# 2. 检查 agent.yaml 内容
cat agents/your_agent/agent.yaml

# 3. 创建基本的 agent.yaml（如果不存在）
mkdir -p agents/your_agent
echo "id: your_agent" > agents/your_agent/agent.yaml
```

**Python 验证**:
```python
from src.agent_template_parser import BatchDataProcessor

processor = BatchDataProcessor("agents")

# 检查可用的 agents
available_agents = processor.get_available_agents()
print("可用的 agents:", available_agents)

# 验证特定 agent
agent_exists = processor.validate_agent_exists("your_agent")
print(f"Agent 'your_agent' 存在: {agent_exists}")
```

### 问题 2: JSON 文件读取失败

**错误信息**:
```
BatchProcessingError: Failed to read 1 JSON files
```

**原因**: JSON 文件格式错误或文件不存在

**解决方案**:
```bash
# 1. 检查文件是否存在
ls -la your_file.json

# 2. 验证 JSON 格式
python -m json.tool your_file.json

# 3. 检查文件编码
file your_file.json
```

**批量验证 JSON 文件**:
```python
import json
import glob

json_files = glob.glob("data/*.json")
for file_path in json_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✅ {file_path}: 格式正确")
    except json.JSONDecodeError as e:
        print(f"❌ {file_path}: JSON 格式错误 - {e}")
    except Exception as e:
        print(f"❌ {file_path}: 读取失败 - {e}")
```

### 问题 3: 内存不足

**错误信息**:
```
MemoryError: Unable to allocate array
```

**原因**: 一次处理的文件过多或文件过大

**解决方案**:
```python
# 分批处理大量文件
def process_in_batches(json_files, batch_size=50):
    processor = BatchDataProcessor()
    
    for i in range(0, len(json_files), batch_size):
        batch = json_files[i:i+batch_size]
        print(f"处理批次 {i//batch_size + 1}/{(len(json_files)-1)//batch_size + 1}")
        
        # 处理当前批次
        json_inputs = []
        for file_path in batch:
            with open(file_path, 'r') as f:
                json_inputs.append(f.read())
        
        processed_data = processor.process_json_inputs(json_inputs, "target_agent")
        testset_data = processor.convert_to_testset_format(processed_data)
        
        # 保存批次结果
        output_file = f"batch_{i//batch_size + 1}.jsonl"
        processor.save_testset(testset_data, "target_agent", output_file)
        
        # 清理内存
        del json_inputs, processed_data, testset_data

# 使用示例
json_files = glob.glob("data/*.json")
process_in_batches(json_files, batch_size=50)
```

## LLM 增强问题

### 问题 1: API Key 未设置

**错误信息**:
```
LLMEnhancementError: OPENAI_API_KEY environment variable is required
```

**解决方案**:
```bash
# 1. 设置环境变量
export OPENAI_API_KEY="your-api-key-here"

# 2. 或在 .env 文件中设置
echo "OPENAI_API_KEY=your-api-key-here" >> .env

# 3. 验证设置
echo $OPENAI_API_KEY

# 4. 或者禁用 LLM 增强
python -m src.agent_template_parser.cli create-agent \
  --system-prompt ... \
  --user-input ... \
  --test-case ... \
  --agent-name ... \
  --no-llm-enhancement
```

### 问题 2: API 调用失败

**错误信息**:
```
LLMEnhancementError: Failed to optimize config with LLM (error: Rate limit exceeded)
```

**原因**: API 调用频率限制或网络问题

**解决方案**:
```python
from src.agent_template_parser import LLMEnhancer

# 配置重试和回退
enhancer = LLMEnhancer(
    model_name="gpt-4",
    max_retries=5,  # 增加重试次数
    fallback_enabled=True  # 启用回退机制
)

# 或者使用更便宜的模型
enhancer = LLMEnhancer(model_name="gpt-3.5-turbo")
```

### 问题 3: LLM 响应格式错误

**错误信息**:
```
LLMEnhancementError: Invalid JSON response from LLM
```

**解决方案**:
```python
# 检查 LLM 响应
import json

def debug_llm_response(config):
    enhancer = LLMEnhancer()
    try:
        result = enhancer.optimize_config(config)
        print("LLM 增强成功")
        return result
    except Exception as e:
        print(f"LLM 增强失败: {e}")
        # 使用回退机制
        return enhancer._optimize_config_fallback(config)
```

## 文件操作错误

### 问题 1: 权限不足

**错误信息**:
```
PermissionError: [Errno 13] Permission denied: 'agents/your_agent/agent.yaml'
```

**解决方案**:
```bash
# 1. 检查文件权限
ls -la agents/your_agent/

# 2. 修改权限
chmod 755 agents/your_agent/
chmod 644 agents/your_agent/agent.yaml

# 3. 检查目录所有者
ls -la agents/

# 4. 如果需要，修改所有者
sudo chown -R $USER:$USER agents/
```

### 问题 2: 磁盘空间不足

**错误信息**:
```
OSError: [Errno 28] No space left on device
```

**解决方案**:
```bash
# 1. 检查磁盘空间
df -h

# 2. 清理临时文件
rm -rf /tmp/*
rm -rf ~/.cache/*

# 3. 检查项目目录大小
du -sh agents/
du -sh templates/
du -sh data/

# 4. 清理不需要的文件
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

### 问题 3: 文件锁定

**错误信息**:
```
PermissionError: [Errno 13] Permission denied: 'agents/your_agent/agent.yaml'
```

**原因**: 文件被其他进程占用

**解决方案**:
```bash
# 1. 查找占用文件的进程
lsof agents/your_agent/agent.yaml

# 2. 结束占用进程
kill -9 <PID>

# 3. 或者重启相关服务
sudo systemctl restart your_service
```

## 性能问题

### 问题 1: 处理速度慢

**症状**: 批量处理大量文件时速度很慢

**解决方案**:
```python
import time
import concurrent.futures
from pathlib import Path

def process_single_file(file_path):
    """处理单个文件"""
    processor = BatchDataProcessor()
    
    with open(file_path, 'r') as f:
        json_input = f.read()
    
    processed_data = processor.process_json_inputs([json_input], "target_agent")
    return processor.convert_to_testset_format(processed_data)

def parallel_process_files(json_files, max_workers=4):
    """并行处理文件"""
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, file_path): file_path 
            for file_path in json_files
        }
        
        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                result = future.result()
                results.extend(result)
                print(f"✅ 处理完成: {file_path}")
            except Exception as e:
                print(f"❌ 处理失败: {file_path} - {e}")
    
    return results

# 使用示例
json_files = list(Path("data").glob("*.json"))
start_time = time.time()
results = parallel_process_files(json_files, max_workers=4)
end_time = time.time()

print(f"处理 {len(json_files)} 个文件，耗时 {end_time - start_time:.2f} 秒")
```

### 问题 2: 内存使用过高

**症状**: 处理大文件时内存占用过高

**解决方案**:
```python
import gc

def memory_efficient_processing(json_files, target_agent):
    """内存高效的处理方式"""
    processor = BatchDataProcessor()
    output_file = f"agents/{target_agent}/testsets/stream_output.jsonl"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, file_path in enumerate(json_files):
            # 处理单个文件
            with open(file_path, 'r') as input_f:
                json_input = input_f.read()
            
            processed_data = processor.process_json_inputs([json_input], target_agent)
            testset_data = processor.convert_to_testset_format(processed_data)
            
            # 立即写入文件
            for entry in testset_data:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            # 清理内存
            del json_input, processed_data, testset_data
            
            # 定期强制垃圾回收
            if i % 100 == 0:
                gc.collect()
                print(f"已处理 {i+1}/{len(json_files)} 个文件")
    
    print(f"所有文件处理完成，输出保存到: {output_file}")
```

## 调试工具

### 1. 启用详细日志

```python
import logging

# 设置日志级别
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 或者只启用特定模块的日志
logger = logging.getLogger('src.agent_template_parser')
logger.setLevel(logging.DEBUG)
```

### 2. 组件单独测试

```python
# 测试模板解析器
from src.agent_template_parser import TemplateParser

def test_template_parser():
    parser = TemplateParser()
    
    # 测试系统提示词解析
    system_prompt = "你是 {role}，处理 ${sys.user_input}"
    try:
        result = parser.parse_system_prompt(system_prompt)
        print("✅ 系统提示词解析成功:", result['variables'])
    except Exception as e:
        print("❌ 系统提示词解析失败:", e)
    
    # 测试用户输入解析
    user_input = "请处理 {input_text}"
    try:
        result = parser.parse_user_input(user_input)
        print("✅ 用户输入解析成功:", result['variables'])
    except Exception as e:
        print("❌ 用户输入解析失败:", e)

test_template_parser()
```

### 3. 配置验证工具

```python
import yaml
import json

def validate_agent_config(agent_name):
    """验证 agent 配置的完整性"""
    agent_dir = Path(f"agents/{agent_name}")
    
    # 检查目录结构
    required_dirs = ["prompts", "testsets"]
    for dir_name in required_dirs:
        dir_path = agent_dir / dir_name
        if not dir_path.exists():
            print(f"❌ 缺少目录: {dir_path}")
        else:
            print(f"✅ 目录存在: {dir_path}")
    
    # 检查 agent.yaml
    agent_yaml = agent_dir / "agent.yaml"
    if agent_yaml.exists():
        try:
            with open(agent_yaml, 'r') as f:
                config = yaml.safe_load(f)
            
            required_keys = ['id', 'flows', 'evaluation']
            missing_keys = [key for key in required_keys if key not in config]
            
            if missing_keys:
                print(f"❌ agent.yaml 缺少字段: {missing_keys}")
            else:
                print("✅ agent.yaml 格式正确")
                
        except Exception as e:
            print(f"❌ agent.yaml 格式错误: {e}")
    else:
        print(f"❌ 缺少文件: {agent_yaml}")
    
    # 检查 prompt 文件
    prompts_dir = agent_dir / "prompts"
    if prompts_dir.exists():
        prompt_files = list(prompts_dir.glob("*.yaml"))
        if prompt_files:
            print(f"✅ 找到 {len(prompt_files)} 个 prompt 文件")
        else:
            print("❌ 没有找到 prompt 文件")

# 使用示例
validate_agent_config("your_agent")
```

### 4. 性能分析工具

```python
import time
import psutil
import os

def profile_function(func, *args, **kwargs):
    """分析函数性能"""
    process = psutil.Process(os.getpid())
    
    # 记录开始状态
    start_time = time.time()
    start_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # 执行函数
    try:
        result = func(*args, **kwargs)
        success = True
    except Exception as e:
        result = e
        success = False
    
    # 记录结束状态
    end_time = time.time()
    end_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # 输出分析结果
    print(f"函数: {func.__name__}")
    print(f"执行时间: {end_time - start_time:.2f} 秒")
    print(f"内存使用: {end_memory - start_memory:.2f} MB")
    print(f"执行状态: {'成功' if success else '失败'}")
    
    if not success:
        print(f"错误信息: {result}")
    
    return result if success else None

# 使用示例
from src.agent_template_parser import BatchDataProcessor

processor = BatchDataProcessor()
json_inputs = ['{"sys": {"user_input": []}, "field": "value"}'] * 100

result = profile_function(
    processor.process_json_inputs,
    json_inputs,
    "test_agent"
)
```

## 获取帮助

如果以上解决方案都无法解决您的问题，请：

1. **检查日志**: 启用详细日志记录，查看具体错误信息
2. **最小化复现**: 创建最小的测试用例来复现问题
3. **收集信息**: 记录错误信息、环境信息、操作步骤
4. **查看文档**: 参考 README.md 和 USAGE_GUIDE.md
5. **提交 Issue**: 在项目仓库中创建详细的问题报告

### 问题报告模板

```markdown
## 问题描述
[简要描述遇到的问题]

## 环境信息
- 操作系统: [如 macOS 12.0]
- Python 版本: [如 3.9.0]
- 项目版本: [如 v1.0.0]

## 复现步骤
1. [第一步]
2. [第二步]
3. [第三步]

## 期望结果
[描述期望的正确行为]

## 实际结果
[描述实际发生的情况]

## 错误信息
```
[粘贴完整的错误信息]
```

## 相关文件
[如果可能，提供相关的模板文件或配置文件]
```

---

希望这个故障排除指南能帮助您快速解决问题。如果您发现了新的问题或解决方案，欢迎贡献到这个文档中！