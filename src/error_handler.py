# src/error_handler.py
"""
全面的错误处理系统

提供分类错误处理，包括配置、执行、数据错误，
并提供清晰的中文错误消息和修复建议。
"""

from __future__ import annotations

import traceback
import logging
from typing import Dict, List, Any, Optional, Union, Type
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ErrorCategory(Enum):
    """错误类别"""
    CONFIGURATION = "configuration"  # 配置错误
    EXECUTION = "execution"         # 执行错误
    DATA = "data"                   # 数据错误
    NETWORK = "network"             # 网络错误
    PERMISSION = "permission"       # 权限错误
    RESOURCE = "resource"           # 资源错误
    VALIDATION = "validation"       # 验证错误
    UNKNOWN = "unknown"             # 未知错误


class ErrorSeverity(Enum):
    """错误严重程度"""
    CRITICAL = "critical"    # 严重错误，无法继续
    HIGH = "high"           # 高级错误，影响主要功能
    MEDIUM = "medium"       # 中级错误，影响部分功能
    LOW = "low"             # 低级错误，轻微影响
    WARNING = "warning"     # 警告，不影响功能


@dataclass
class ErrorInfo:
    """错误信息"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    suggestion: str
    details: Optional[str] = None
    error_code: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "details": self.details,
            "error_code": self.error_code,
            "context": self.context
        }


class PipelineError(Exception):
    """Pipeline 基础错误类"""
    
    def __init__(self, 
                 message: str,
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 suggestion: str = "",
                 error_code: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.suggestion = suggestion
        self.error_code = error_code
        self.context = context or {}
    
    def get_error_info(self) -> ErrorInfo:
        """获取错误信息"""
        return ErrorInfo(
            category=self.category,
            severity=self.severity,
            message=str(self),
            suggestion=self.suggestion,
            error_code=self.error_code,
            context=self.context
        )


class ConfigurationError(PipelineError):
    """配置错误"""
    
    def __init__(self, message: str, suggestion: str = "", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            suggestion=suggestion or "请检查配置文件格式和内容",
            **kwargs
        )


class ExecutionError(PipelineError):
    """执行错误"""
    
    def __init__(self, message: str, suggestion: str = "", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.EXECUTION,
            severity=ErrorSeverity.MEDIUM,
            suggestion=suggestion or "请检查执行环境和参数",
            **kwargs
        )


class DataError(PipelineError):
    """数据错误"""
    
    def __init__(self, message: str, suggestion: str = "", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.MEDIUM,
            suggestion=suggestion or "请检查数据文件格式和内容",
            **kwargs
        )


class NetworkError(PipelineError):
    """网络错误"""
    
    def __init__(self, message: str, suggestion: str = "", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            suggestion=suggestion or "请检查网络连接和API配置",
            **kwargs
        )


class ValidationError(PipelineError):
    """验证错误"""
    
    def __init__(self, message: str, suggestion: str = "", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            suggestion=suggestion or "请检查输入数据的格式和有效性",
            **kwargs
        )


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化错误处理器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
        self.error_patterns = self._init_error_patterns()
    
    def _init_error_patterns(self) -> Dict[str, ErrorInfo]:
        """初始化错误模式匹配"""
        return {
            # 配置错误
            "yaml.scanner.ScannerError": ErrorInfo(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                message="YAML 配置文件格式错误",
                suggestion="请检查 YAML 文件的缩进、引号和特殊字符，确保格式正确"
            ),
            "FileNotFoundError": ErrorInfo(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                message="配置文件或数据文件不存在",
                suggestion="请确认文件路径正确，文件存在且有读取权限"
            ),
            "KeyError": ErrorInfo(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.MEDIUM,
                message="配置项缺失",
                suggestion="请检查配置文件是否包含所有必需的字段"
            ),
            
            # 执行错误
            "ConnectionError": ErrorInfo(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                message="网络连接失败",
                suggestion="请检查网络连接，确认 API 服务可访问"
            ),
            "TimeoutError": ErrorInfo(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                message="请求超时",
                suggestion="请检查网络状况，考虑增加超时时间或重试"
            ),
            "AuthenticationError": ErrorInfo(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                message="API 认证失败",
                suggestion="请检查 API 密钥配置是否正确，确认密钥有效且有足够权限"
            ),
            
            # 数据错误
            "json.JSONDecodeError": ErrorInfo(
                category=ErrorCategory.DATA,
                severity=ErrorSeverity.MEDIUM,
                message="JSON 数据格式错误",
                suggestion="请检查 JSON 文件格式，确保语法正确"
            ),
            "UnicodeDecodeError": ErrorInfo(
                category=ErrorCategory.DATA,
                severity=ErrorSeverity.MEDIUM,
                message="文件编码错误",
                suggestion="请确认文件使用 UTF-8 编码保存"
            ),
            
            # 权限错误
            "PermissionError": ErrorInfo(
                category=ErrorCategory.PERMISSION,
                severity=ErrorSeverity.HIGH,
                message="文件权限不足",
                suggestion="请检查文件和目录的读写权限"
            ),
            
            # 资源错误
            "MemoryError": ErrorInfo(
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                message="内存不足",
                suggestion="请减少批处理大小或增加系统内存"
            ),
            "OSError": ErrorInfo(
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.HIGH,
                message="系统资源错误",
                suggestion="请检查磁盘空间和系统资源使用情况"
            )
        }
    
    def handle_error(self, 
                    error: Exception, 
                    context: Optional[Dict[str, Any]] = None,
                    reraise: bool = True) -> ErrorInfo:
        """
        处理错误
        
        Args:
            error: 异常对象
            context: 错误上下文信息
            reraise: 是否重新抛出异常
            
        Returns:
            错误信息对象
        """
        # 如果是已知的 Pipeline 错误，直接返回错误信息
        if isinstance(error, PipelineError):
            error_info = error.get_error_info()
            if context:
                error_info.context.update(context)
        else:
            # 分析未知错误
            error_info = self._analyze_error(error, context)
        
        # 记录错误
        self._log_error(error_info, error)
        
        # 重新抛出异常（如果需要）
        if reraise:
            if isinstance(error, PipelineError):
                raise error
            else:
                # 将未知错误包装为 Pipeline 错误
                raise ExecutionError(
                    message=error_info.message,
                    suggestion=error_info.suggestion,
                    context=error_info.context
                ) from error
        
        return error_info
    
    def _analyze_error(self, 
                      error: Exception, 
                      context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """分析未知错误"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # 尝试匹配已知错误模式
        if error_type in self.error_patterns:
            pattern = self.error_patterns[error_type]
            return ErrorInfo(
                category=pattern.category,
                severity=pattern.severity,
                message=f"{pattern.message}: {error_message}",
                suggestion=pattern.suggestion,
                details=self._get_error_details(error),
                context=context
            )
        
        # 基于错误消息进行模式匹配
        for pattern_key, pattern_info in self.error_patterns.items():
            if pattern_key.lower() in error_message.lower():
                return ErrorInfo(
                    category=pattern_info.category,
                    severity=pattern_info.severity,
                    message=f"{pattern_info.message}: {error_message}",
                    suggestion=pattern_info.suggestion,
                    details=self._get_error_details(error),
                    context=context
                )
        
        # 未知错误的默认处理
        return ErrorInfo(
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            message=f"未知错误 ({error_type}): {error_message}",
            suggestion="请检查错误详情，如果问题持续存在，请联系技术支持",
            details=self._get_error_details(error),
            context=context
        )
    
    def _get_error_details(self, error: Exception) -> str:
        """获取错误详情"""
        return traceback.format_exc()
    
    def _log_error(self, error_info: ErrorInfo, original_error: Exception):
        """记录错误日志"""
        log_level = {
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING
        }.get(error_info.severity, logging.ERROR)
        
        log_message = f"[{error_info.category.value.upper()}] {error_info.message}"
        if error_info.suggestion:
            log_message += f" | 建议: {error_info.suggestion}"
        
        self.logger.log(log_level, log_message)
        
        # 记录详细信息（调试级别）
        if error_info.details:
            self.logger.debug(f"错误详情:\n{error_info.details}")
        
        if error_info.context:
            self.logger.debug(f"错误上下文: {error_info.context}")
    
    def format_error_message(self, error_info: ErrorInfo) -> str:
        """格式化错误消息"""
        severity_icons = {
            ErrorSeverity.CRITICAL: "🔴",
            ErrorSeverity.HIGH: "🟠", 
            ErrorSeverity.MEDIUM: "🟡",
            ErrorSeverity.LOW: "🔵",
            ErrorSeverity.WARNING: "⚠️"
        }
        
        category_names = {
            ErrorCategory.CONFIGURATION: "配置错误",
            ErrorCategory.EXECUTION: "执行错误",
            ErrorCategory.DATA: "数据错误",
            ErrorCategory.NETWORK: "网络错误",
            ErrorCategory.PERMISSION: "权限错误",
            ErrorCategory.RESOURCE: "资源错误",
            ErrorCategory.VALIDATION: "验证错误",
            ErrorCategory.UNKNOWN: "未知错误"
        }
        
        icon = severity_icons.get(error_info.severity, "❌")
        category_name = category_names.get(error_info.category, "未知类别")
        
        message = f"{icon} {category_name}: {error_info.message}"
        
        if error_info.suggestion:
            message += f"\n💡 建议: {error_info.suggestion}"
        
        if error_info.error_code:
            message += f"\n🔍 错误代码: {error_info.error_code}"
        
        return message


class ErrorCollector:
    """错误收集器"""
    
    def __init__(self):
        """初始化错误收集器"""
        self.errors: List[ErrorInfo] = []
        self.warnings: List[ErrorInfo] = []
    
    def add_error(self, error_info: ErrorInfo):
        """添加错误"""
        if error_info.severity == ErrorSeverity.WARNING:
            self.warnings.append(error_info)
        else:
            self.errors.append(error_info)
    
    def add_exception(self, 
                     error: Exception, 
                     context: Optional[Dict[str, Any]] = None,
                     error_handler: Optional[ErrorHandler] = None):
        """添加异常"""
        handler = error_handler or ErrorHandler()
        error_info = handler.handle_error(error, context, reraise=False)
        self.add_error(error_info)
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        error_counts = {}
        warning_counts = {}
        
        for error in self.errors:
            category = error.category.value
            error_counts[category] = error_counts.get(category, 0) + 1
        
        for warning in self.warnings:
            category = warning.category.value
            warning_counts[category] = warning_counts.get(category, 0) + 1
        
        return {
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "error_counts": error_counts,
            "warning_counts": warning_counts,
            "critical_errors": len([e for e in self.errors if e.severity == ErrorSeverity.CRITICAL]),
            "high_errors": len([e for e in self.errors if e.severity == ErrorSeverity.HIGH])
        }
    
    def format_summary(self) -> str:
        """格式化摘要"""
        if not self.has_errors() and not self.has_warnings():
            return "✅ 没有发现错误或警告"
        
        summary = self.get_error_summary()
        lines = []
        
        if summary["total_errors"] > 0:
            lines.append(f"❌ 发现 {summary['total_errors']} 个错误")
            
            if summary["critical_errors"] > 0:
                lines.append(f"  🔴 严重错误: {summary['critical_errors']} 个")
            
            if summary["high_errors"] > 0:
                lines.append(f"  🟠 高级错误: {summary['high_errors']} 个")
        
        if summary["total_warnings"] > 0:
            lines.append(f"⚠️ 发现 {summary['total_warnings']} 个警告")
        
        return "\n".join(lines)
    
    def clear(self):
        """清空错误和警告"""
        self.errors.clear()
        self.warnings.clear()


# 全局错误处理器实例
_global_error_handler = ErrorHandler()
_global_error_collector = ErrorCollector()


def handle_error(error: Exception, 
                context: Optional[Dict[str, Any]] = None,
                reraise: bool = True) -> ErrorInfo:
    """全局错误处理函数"""
    return _global_error_handler.handle_error(error, context, reraise)


def collect_error(error: Exception, 
                 context: Optional[Dict[str, Any]] = None):
    """收集错误到全局收集器"""
    _global_error_collector.add_exception(error, context, _global_error_handler)


def get_error_collector() -> ErrorCollector:
    """获取全局错误收集器"""
    return _global_error_collector


def format_error(error_info: ErrorInfo) -> str:
    """格式化错误消息"""
    return _global_error_handler.format_error_message(error_info)


# 常用错误创建函数
def create_config_error(message: str, 
                       suggestion: str = "",
                       file_path: Optional[str] = None) -> ConfigurationError:
    """创建配置错误"""
    context = {"file_path": file_path} if file_path else None
    return ConfigurationError(message, suggestion, context=context)


def create_data_error(message: str,
                     suggestion: str = "",
                     file_path: Optional[str] = None,
                     line_number: Optional[int] = None) -> DataError:
    """创建数据错误"""
    context = {}
    if file_path:
        context["file_path"] = file_path
    if line_number:
        context["line_number"] = line_number
    
    return DataError(message, suggestion, context=context if context else None)


def create_execution_error(message: str,
                          suggestion: str = "",
                          step_id: Optional[str] = None,
                          sample_id: Optional[str] = None) -> ExecutionError:
    """创建执行错误"""
    context = {}
    if step_id:
        context["step_id"] = step_id
    if sample_id:
        context["sample_id"] = sample_id
    
    return ExecutionError(message, suggestion, context=context if context else None)


def create_network_error(message: str,
                        suggestion: str = "",
                        api_endpoint: Optional[str] = None,
                        status_code: Optional[int] = None) -> NetworkError:
    """创建网络错误"""
    context = {}
    if api_endpoint:
        context["api_endpoint"] = api_endpoint
    if status_code:
        context["status_code"] = status_code
    
    return NetworkError(message, suggestion, context=context if context else None)


def create_validation_error(message: str,
                           suggestion: str = "",
                           field_name: Optional[str] = None,
                           field_value: Optional[Any] = None) -> ValidationError:
    """创建验证错误"""
    context = {}
    if field_name:
        context["field_name"] = field_name
    if field_value is not None:
        context["field_value"] = field_value
    
    return ValidationError(message, suggestion, context=context if context else None)