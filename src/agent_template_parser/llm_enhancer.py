"""LLM增强处理器模块，用于使用LLM修正和优化配置格式。"""

import json
import os
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import yaml
from .models import GeneratedConfig


class LLMEnhancementError(Exception):
    """LLM增强处理错误"""
    pass


class LLMEnhancer:
    """LLM增强处理器，使用OpenAI API进行配置修正和优化"""
    
    def __init__(self, model_name: str = None, temperature: float = 0.1, max_retries: int = 3, fallback_enabled: bool = True):
        """
        初始化LLM增强处理器
        
        Args:
            model_name: 使用的模型名称
            temperature: 模型温度参数
            max_retries: 最大重试次数
            fallback_enabled: 是否启用回退机制
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_retries = max_retries
        self.fallback_enabled = fallback_enabled
        self._llm = None
        
    @property
    def llm(self) -> ChatOpenAI:
        """懒加载LLM实例"""
        if self._llm is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise LLMEnhancementError("OPENAI_API_KEY environment variable is required")
            
            # 如果没有指定模型，使用项目默认配置
            from ..config import get_openai_model_name

            try:
                model_name = self.model_name or get_openai_model_name()
            except EnvironmentError as exc:
                raise LLMEnhancementError(str(exc)) from exc
            
            self._llm = ChatOpenAI(
                model=model_name,
                temperature=self.temperature,
                openai_api_key=api_key
            )
        return self._llm
    
    def fix_config_format(self, config: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """
        使用LLM修正配置格式错误，支持重试和回退机制
        
        Args:
            config: 需要修正的配置
            errors: 检测到的错误列表
            
        Returns:
            修正后的配置
            
        Raises:
            LLMEnhancementError: LLM调用失败且无法回退时抛出
        """
        return self._execute_with_fallback(
            self._fix_config_format_with_llm,
            config,
            errors,
            fallback_func=self._fix_config_format_fallback,
            operation_name="fix config format"
        )
    
    def optimize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM优化配置内容，支持重试和回退机制
        
        Args:
            config: 需要优化的配置
            
        Returns:
            优化后的配置
            
        Raises:
            LLMEnhancementError: LLM调用失败且无法回退时抛出
        """
        return self._execute_with_fallback(
            self._optimize_config_with_llm,
            config,
            fallback_func=self._optimize_config_fallback,
            operation_name="optimize config"
        )
    
    def generate_improvement_suggestions(self, config: Dict[str, Any]) -> List[str]:
        """
        生成配置改进建议，支持重试和回退机制
        
        Args:
            config: 需要分析的配置
            
        Returns:
            改进建议列表
            
        Raises:
            LLMEnhancementError: LLM调用失败且无法回退时抛出
        """
        return self._execute_with_fallback(
            self._generate_suggestions_with_llm,
            config,
            fallback_func=self._generate_suggestions_fallback,
            operation_name="generate suggestions"
        )
    
    def _get_fix_format_system_prompt(self) -> str:
        """获取格式修正的系统提示词"""
        return """你是一个专门修正YAML配置格式的专家。你的任务是根据提供的错误信息修正配置文件格式。

请遵循以下规则：
1. 保持配置的核心功能不变
2. 修正所有格式错误
3. 确保YAML语法正确
4. 保持字段名称和结构的一致性
5. 只返回修正后的YAML配置，不要添加任何解释

返回格式：直接返回修正后的YAML内容，用```yaml包围。"""
    
    def _get_fix_format_user_prompt(self, config: Dict[str, Any], errors: List[str]) -> str:
        """获取格式修正的用户提示词"""
        config_yaml = yaml.dump(config, default_flow_style=False, allow_unicode=True)
        errors_text = "\n".join([f"- {error}" for error in errors])
        
        return f"""请修正以下YAML配置中的格式错误：

检测到的错误：
{errors_text}

当前配置：
```yaml
{config_yaml}
```

请返回修正后的配置。"""
    
    def _get_optimize_config_system_prompt(self) -> str:
        """获取配置优化的系统提示词"""
        return """你是一个专门优化agent配置的专家。你的任务是优化提供的配置文件，使其更加高效和规范。

请遵循以下优化原则：
1. 保持配置的核心功能不变
2. 优化字段命名和结构
3. 添加合适的默认值
4. 确保配置的可读性和维护性
5. 遵循最佳实践

返回格式：直接返回优化后的YAML内容，用```yaml包围。"""
    
    def _get_optimize_config_user_prompt(self, config: Dict[str, Any]) -> str:
        """获取配置优化的用户提示词"""
        config_yaml = yaml.dump(config, default_flow_style=False, allow_unicode=True)
        
        return f"""请优化以下agent配置：

当前配置：
```yaml
{config_yaml}
```

请返回优化后的配置。"""
    
    def _get_suggestions_system_prompt(self) -> str:
        """获取建议生成的系统提示词"""
        return """你是一个专门分析agent配置的专家。你的任务是分析提供的配置文件并生成改进建议。

请从以下方面分析：
1. 配置结构的合理性
2. 字段命名的规范性
3. 默认值的设置
4. 性能优化建议
5. 维护性改进

返回格式：每个建议占一行，以"- "开头。"""
    
    def _get_suggestions_user_prompt(self, config: Dict[str, Any]) -> str:
        """获取建议生成的用户提示词"""
        config_yaml = yaml.dump(config, default_flow_style=False, allow_unicode=True)
        
        return f"""请分析以下agent配置并提供改进建议：

配置内容：
```yaml
{config_yaml}
```

请提供具体的改进建议。"""
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的YAML配置"""
        try:
            # 提取YAML代码块
            if "```yaml" in response:
                start = response.find("```yaml") + 7
                end = response.find("```", start)
                yaml_content = response[start:end].strip()
            else:
                yaml_content = response.strip()
            
            # 解析YAML
            parsed_config = yaml.safe_load(yaml_content)
            
            if not isinstance(parsed_config, dict):
                raise ValueError("Parsed config is not a dictionary")
                
            return parsed_config
            
        except Exception as e:
            raise LLMEnhancementError(f"Failed to parse LLM response: {str(e)}")
    
    def _parse_suggestions_response(self, response: str) -> List[str]:
        """解析LLM返回的建议列表"""
        try:
            suggestions = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('- '):
                    suggestions.append(line[2:].strip())
                elif line and not line.startswith('#'):
                    # 如果不是以"- "开头但有内容，也添加为建议
                    suggestions.append(line)
            
            return suggestions
            
        except Exception as e:
            raise LLMEnhancementError(f"Failed to parse suggestions response: {str(e)}")
    
    def is_available(self) -> bool:
        """检查LLM是否可用"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            return api_key is not None and api_key.strip() != ""
        except Exception:
            return False
    
    def _execute_with_fallback(self, llm_func, *args, fallback_func=None, operation_name="operation"):
        """
        执行LLM操作，支持重试和回退机制
        
        Args:
            llm_func: LLM操作函数
            *args: 传递给LLM函数的参数
            fallback_func: 回退函数
            operation_name: 操作名称，用于错误信息
            
        Returns:
            操作结果
            
        Raises:
            LLMEnhancementError: 所有重试和回退都失败时抛出
        """
        last_error = None
        
        # 尝试LLM操作（带重试）
        for attempt in range(self.max_retries):
            try:
                return llm_func(*args)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # 还有重试机会，继续
                    continue
                else:
                    # 最后一次尝试失败
                    break
        
        # LLM操作失败，尝试回退
        if self.fallback_enabled and fallback_func:
            try:
                return fallback_func(*args)
            except Exception as fallback_error:
                raise LLMEnhancementError(
                    f"Failed to {operation_name} with LLM (error: {last_error}) "
                    f"and fallback also failed (error: {fallback_error})"
                )
        
        # 没有回退或回退被禁用
        raise LLMEnhancementError(f"Failed to {operation_name}: {last_error}")
    
    def _fix_config_format_with_llm(self, config: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """使用LLM修正配置格式的核心实现"""
        system_prompt = self._get_fix_format_system_prompt()
        user_prompt = self._get_fix_format_user_prompt(config, errors)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = self.llm.invoke(messages)
        return self._parse_llm_response(response.content)
    
    def _optimize_config_with_llm(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """使用LLM优化配置的核心实现"""
        system_prompt = self._get_optimize_config_system_prompt()
        user_prompt = self._get_optimize_config_user_prompt(config)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = self.llm.invoke(messages)
        return self._parse_llm_response(response.content)
    
    def _generate_suggestions_with_llm(self, config: Dict[str, Any]) -> List[str]:
        """使用LLM生成建议的核心实现"""
        system_prompt = self._get_suggestions_system_prompt()
        user_prompt = self._get_suggestions_user_prompt(config)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = self.llm.invoke(messages)
        return self._parse_suggestions_response(response.content)
    
    def _fix_config_format_fallback(self, config: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """配置格式修正的回退实现"""
        # 基础的格式修正逻辑
        fixed_config = config.copy()
        
        # 根据错误类型进行基础修正
        for error in errors:
            error_lower = error.lower()
            
            if "description" in error_lower and "missing" in error_lower:
                if "description" not in fixed_config:
                    fixed_config["description"] = f"Auto-generated description for {fixed_config.get('name', 'agent')}"
            
            if "evaluation" in error_lower and "missing" in error_lower:
                if "evaluation" not in fixed_config:
                    fixed_config["evaluation"] = {
                        "case_fields": ["input", "output"]
                    }
            
            if "flows" in error_lower and "missing" in error_lower:
                if "flows" not in fixed_config:
                    fixed_config["flows"] = {
                        "default": {
                            "prompt": f"{fixed_config.get('name', 'agent')}_v1"
                        }
                    }
        
        return fixed_config
    
    def _optimize_config_fallback(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """配置优化的回退实现"""
        # 基础的优化逻辑
        optimized_config = config.copy()
        
        # 添加常见的优化字段
        if "description" not in optimized_config and "name" in optimized_config:
            optimized_config["description"] = f"Agent configuration for {optimized_config['name']}"
        
        # 确保flows配置完整
        if "flows" in optimized_config:
            for flow_name, flow_config in optimized_config["flows"].items():
                if isinstance(flow_config, dict) and "timeout" not in flow_config:
                    flow_config["timeout"] = 30  # 默认30秒超时
        
        # 确保evaluation配置完整
        if "evaluation" in optimized_config:
            eval_config = optimized_config["evaluation"]
            if isinstance(eval_config, dict):
                if "case_fields" not in eval_config:
                    eval_config["case_fields"] = ["input", "output"]
                if "metrics" not in eval_config:
                    eval_config["metrics"] = ["accuracy"]
        
        return optimized_config
    
    def _generate_suggestions_fallback(self, config: Dict[str, Any]) -> List[str]:
        """生成建议的回退实现"""
        suggestions = []
        
        # 基于配置内容生成基础建议
        if "description" not in config:
            suggestions.append("添加description字段以提高配置的可读性")
        
        if "flows" in config:
            flows = config["flows"]
            if isinstance(flows, dict):
                for flow_name, flow_config in flows.items():
                    if isinstance(flow_config, dict) and "timeout" not in flow_config:
                        suggestions.append(f"为flow '{flow_name}' 添加timeout配置")
        
        if "evaluation" in config:
            eval_config = config["evaluation"]
            if isinstance(eval_config, dict):
                if "metrics" not in eval_config:
                    suggestions.append("在evaluation配置中添加metrics字段")
                if len(eval_config.get("case_fields", [])) < 2:
                    suggestions.append("考虑在case_fields中添加更多字段")
        
        if not suggestions:
            suggestions.append("配置看起来已经比较完整，可以考虑添加更多自定义字段")
        
        return suggestions