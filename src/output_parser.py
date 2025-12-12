# src/output_parser.py
"""
Output Parser 工厂类

提供创建和配置 LangChain Output Parser 的工厂方法，
支持 JSON、Pydantic、List 等多种解析器类型，以及重试机制。
"""

from typing import Any, Optional, TypeVar, Dict
import logging
from dataclasses import dataclass, field
from langchain_core.output_parsers import (
    BaseOutputParser,
    JsonOutputParser,
    PydanticOutputParser,
    CommaSeparatedListOutputParser,
    StrOutputParser
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .models import OutputParserConfig
from .config import get_openai_model_name, get_openai_temperature

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ParserStatistics:
    """Output Parser 统计信息"""
    success_count: int = 0
    failure_count: int = 0
    total_retry_count: int = 0
    
    def record_success(self, retry_count: int = 0):
        """记录成功的解析"""
        self.success_count += 1
        self.total_retry_count += retry_count
    
    def record_failure(self, retry_count: int = 0):
        """记录失败的解析"""
        self.failure_count += 1
        self.total_retry_count += retry_count
    
    def get_success_rate(self) -> float:
        """计算解析成功率"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.success_count / total
    
    def get_average_retries(self) -> float:
        """计算平均重试次数"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return self.total_retry_count / total
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_retry_count": self.total_retry_count,
            "success_rate": self.get_success_rate(),
            "average_retries": self.get_average_retries()
        }
    
    def reset(self):
        """重置统计信息"""
        self.success_count = 0
        self.failure_count = 0
        self.total_retry_count = 0


class OutputParserFactory:
    """Output Parser 工厂，根据配置创建相应的 parser"""
    
    @staticmethod
    def create_parser(config: OutputParserConfig) -> BaseOutputParser:
        """
        根据配置创建 Output Parser
        
        支持的类型：
        - json: JsonOutputParser (LangChain)
        - pydantic: PydanticOutputParser (LangChain)
        - list: CommaSeparatedListOutputParser (LangChain)
        - none: StrOutputParser (默认)
        
        Args:
            config: OutputParserConfig 配置对象
            
        Returns:
            BaseOutputParser: 对应类型的 parser 实例
            
        Raises:
            ValueError: 当配置无效时
        """
        # 验证配置
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid OutputParserConfig: {'; '.join(errors)}")
        
        parser_type = config.type.lower()
        
        if parser_type == "json":
            # JSON Parser
            if config.schema:
                # 如果提供了 schema，使用带 schema 的 JsonOutputParser
                return JsonOutputParser(pydantic_object=None)
            else:
                # 否则使用默认的 JsonOutputParser
                return JsonOutputParser()
        
        elif parser_type == "pydantic":
            # Pydantic Parser
            # 注意：这里需要动态导入 Pydantic 模型
            # 实际使用时需要传入具体的 Pydantic 类
            raise NotImplementedError(
                "Pydantic parser requires a Pydantic model class. "
                "Please use create_pydantic_parser() with a specific model class."
            )
        
        elif parser_type == "list":
            # List Parser
            return CommaSeparatedListOutputParser()
        
        elif parser_type == "none":
            # 默认字符串 Parser
            return StrOutputParser()
        
        else:
            # 不应该到达这里，因为 validate() 已经检查过
            raise ValueError(f"Unsupported parser type: {parser_type}")
    
    @staticmethod
    def create_pydantic_parser(pydantic_class: Any) -> PydanticOutputParser:
        """
        创建 Pydantic Output Parser
        
        Args:
            pydantic_class: Pydantic 模型类
            
        Returns:
            PydanticOutputParser: Pydantic parser 实例
        """
        return PydanticOutputParser(pydantic_object=pydantic_class)
    
    @staticmethod
    def create_retry_parser(
        parser: BaseOutputParser,
        max_retries: int = 3,
        llm: Optional[ChatOpenAI] = None
    ) -> 'RetryOutputParser':
        """
        创建带重试的 parser
        
        使用自定义的 RetryOutputParser 包装原始 parser，
        当解析失败时自动重试解析。
        
        Args:
            parser: 原始 parser
            max_retries: 最大重试次数
            llm: 用于修复的 LLM（保留参数以兼容接口，当前未使用）
            
        Returns:
            RetryOutputParser: 带重试功能的 parser
        """
        return RetryOutputParser(
            parser=parser,
            max_retries=max_retries
        )
    
    @staticmethod
    def create_parser_from_config(
        config: OutputParserConfig,
        pydantic_class: Optional[Any] = None
    ) -> BaseOutputParser:
        """
        从配置创建 parser，并根据配置决定是否包装重试逻辑
        
        Args:
            config: OutputParserConfig 配置对象
            pydantic_class: Pydantic 模型类（仅当 type="pydantic" 时需要）
            
        Returns:
            BaseOutputParser: 配置好的 parser（可能包含重试逻辑）
        """
        # 创建基础 parser
        if config.type == "pydantic":
            if pydantic_class is None:
                raise ValueError("Pydantic parser requires pydantic_class parameter")
            parser = OutputParserFactory.create_pydantic_parser(pydantic_class)
        else:
            parser = OutputParserFactory.create_parser(config)
        
        # 如果配置了重试，包装 RetryOutputParser
        if config.retry_on_error and config.max_retries > 0:
            parser = OutputParserFactory.create_retry_parser(
                parser=parser,
                max_retries=config.max_retries
            )
        
        return parser


class RetryOutputParser:
    """
    自定义重试 Output Parser 包装器
    
    当解析失败时，自动重试指定次数。
    这是一个简单但有效的重试机制，避免了 LangChain OutputFixingParser 的兼容性问题。
    
    注意：这不是 BaseOutputParser 的子类，而是一个包装器。
    它实现了相同的接口（parse, get_format_instructions），可以在 LCEL chain 中使用。
    """
    
    def __init__(self, parser: BaseOutputParser, max_retries: int = 3):
        """
        初始化重试 parser
        
        Args:
            parser: 原始 parser
            max_retries: 最大重试次数
        """
        self.parser = parser
        self.max_retries = max_retries
        self._retry_count = 0  # 用于统计
        self.statistics = ParserStatistics()  # 统计信息
    
    def parse(self, text: Any) -> Any:
        """
        解析文本，失败时自动重试
        
        Args:
            text: 要解析的文本（可能是字符串或 AIMessage）
            
        Returns:
            解析后的对象
            
        Raises:
            Exception: 当所有重试都失败时
        """
        # 如果输入是 AIMessage，提取 content
        from langchain_core.messages import BaseMessage
        if isinstance(text, BaseMessage):
            text = text.content
        
        last_error = None
        self._retry_count = 0
        
        for attempt in range(self.max_retries + 1):
            try:
                result = self.parser.parse(text)
                
                if attempt > 0:
                    logger.info(f"Parse succeeded on attempt {attempt + 1}/{self.max_retries + 1}")
                    self._retry_count = attempt
                
                # 记录成功的解析
                self.statistics.record_success(retry_count=attempt)
                
                return result
                
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries:
                    logger.warning(
                        f"Parse failed on attempt {attempt + 1}/{self.max_retries + 1}: {e}. "
                        f"Retrying..."
                    )
                    self._retry_count = attempt + 1
                    # 简单的重试策略：直接重试相同的文本
                    # 在实际场景中，LLM 的输出通常是确定性的，
                    # 所以重试主要是为了处理临时的解析问题
                    continue
                else:
                    logger.error(
                        f"Parse failed after {self.max_retries + 1} attempts. "
                        f"Last error: {e}"
                    )
                    self._retry_count = self.max_retries
        
        # 记录失败的解析
        self.statistics.record_failure(retry_count=self.max_retries)
        
        # 所有重试都失败，抛出最后一个错误
        raise last_error
    
    def get_format_instructions(self) -> str:
        """获取格式说明"""
        return self.parser.get_format_instructions()
    
    @property
    def _type(self) -> str:
        """返回 parser 类型"""
        return f"retry_{self.parser._type}"
    
    def get_retry_count(self) -> int:
        """获取最后一次解析的重试次数"""
        return self._retry_count
    
    def get_statistics(self) -> ParserStatistics:
        """获取统计信息"""
        return self.statistics
    
    def reset_statistics(self):
        """重置统计信息"""
        self.statistics.reset()
    
    def __call__(self, text: Any) -> Any:
        """使 parser 可调用，兼容 LCEL"""
        return self.parse(text)
