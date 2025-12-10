#!/usr/bin/env python3
"""
测试运行器脚本

运行所有单元测试并生成覆盖率报告
"""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """运行测试套件"""
    print("🧪 开始运行单元测试...")
    
    # 确保在项目根目录
    project_root = Path(__file__).parent
    
    try:
        # 运行 pytest 并生成覆盖率报告
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=85"  # 要求至少 85% 覆盖率
        ]
        
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        
        print("📊 测试输出:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  错误输出:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ 所有测试通过！")
            print("📈 覆盖率报告已生成到 htmlcov/ 目录")
        else:
            print("❌ 测试失败或覆盖率不足")
            return False
            
    except FileNotFoundError:
        print("❌ pytest 未安装，请运行: pip install pytest pytest-cov")
        return False
    except Exception as e:
        print(f"❌ 运行测试时出错: {e}")
        return False
    
    return True

def install_test_dependencies():
    """安装测试依赖"""
    print("📦 安装测试依赖...")
    
    dependencies = [
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-mock>=3.10.0"
    ]
    
    for dep in dependencies:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True)
            print(f"✅ 已安装: {dep}")
        except subprocess.CalledProcessError as e:
            print(f"❌ 安装失败: {dep} - {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("🚀 Pipeline Regression System - 单元测试")
    print("=" * 50)
    
    # 检查并安装依赖
    try:
        import pytest
        import pytest_cov
    except ImportError:
        print("📦 缺少测试依赖，正在安装...")
        if not install_test_dependencies():
            sys.exit(1)
    
    # 运行测试
    success = run_tests()
    
    if success:
        print("\n🎉 测试完成！")
        print("💡 提示: 查看 htmlcov/index.html 获取详细覆盖率报告")
        sys.exit(0)
    else:
        print("\n💥 测试失败！")
        sys.exit(1)