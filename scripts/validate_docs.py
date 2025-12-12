#!/usr/bin/env python3
"""
文档一致性验证脚本

检查文档链接的有效性和示例代码的可运行性。
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def check_file_exists(file_path: str, base_dir: Path) -> bool:
    """检查文件是否存在"""
    full_path = base_dir / file_path
    return full_path.exists()

def extract_markdown_links(content: str) -> List[Tuple[str, str]]:
    """从 Markdown 内容中提取链接"""
    # 匹配 [text](link) 格式
    pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    return re.findall(pattern, content)

def validate_documentation():
    """验证文档一致性"""
    project_root = Path(__file__).parent.parent
    errors = []
    warnings = []
    
    print("=" * 60)
    print("文档一致性验证")
    print("=" * 60)
    
    # 1. 检查 README.md 中的链接
    print("\n1. 检查 README.md 中的文档链接...")
    readme_path = project_root / "README.md"
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        links = extract_markdown_links(readme_content)
        doc_links = [(text, link) for text, link in links if link.startswith('docs/') or link.endswith('.md')]
        
        for text, link in doc_links:
            # 移除锚点
            file_link = link.split('#')[0]
            if file_link and not check_file_exists(file_link, project_root):
                errors.append(f"  ❌ 链接失效: [{text}]({link})")
            else:
                print(f"  ✅ [{text}]({link})")
    else:
        errors.append("  ❌ README.md 不存在")
    
    # 2. 检查核心文档是否存在
    print("\n2. 检查核心文档...")
    core_docs = [
        "docs/USAGE_GUIDE.md",
        "docs/ARCHITECTURE.md",
        "docs/ARCHITECTURE_ANALYSIS.md",
        "docs/TROUBLESHOOTING.md"
    ]
    
    for doc in core_docs:
        if check_file_exists(doc, project_root):
            print(f"  ✅ {doc}")
        else:
            errors.append(f"  ❌ 缺少核心文档: {doc}")
    
    # 3. 检查参考文档
    print("\n3. 检查参考文档...")
    reference_docs = [
        "docs/reference/pipeline-guide.md",
        "docs/reference/output-parser-guide.md",
        "docs/reference/eval-modes-guide.md",
        "docs/reference/regression-testing.md",
        "docs/reference/data-structure-guide.md",
        "docs/reference/evaluation-rules.md",
        "docs/reference/manual-eval-guide.md",
        "docs/reference/project-structure.md",
        "docs/reference/migration-guide.md"
    ]
    
    for doc in reference_docs:
        if check_file_exists(doc, project_root):
            print(f"  ✅ {doc}")
        else:
            warnings.append(f"  ⚠️  参考文档缺失: {doc}")
    
    # 4. 检查示例文件
    print("\n4. 检查示例文件...")
    examples = [
        "examples/pipeline_demo.py",
        "pipelines/document_summary.yaml",
        "pipelines/customer_service_flow.yaml"
    ]
    
    for example in examples:
        if check_file_exists(example, project_root):
            print(f"  ✅ {example}")
        else:
            errors.append(f"  ❌ 缺少示例文件: {example}")
    
    # 5. 检查 Output Parser 文档
    print("\n5. 检查 Output Parser 文档...")
    output_parser_docs = [
        "OUTPUT_PARSER_USAGE.md",
        "docs/reference/output-parser-guide.md"
    ]
    
    for doc in output_parser_docs:
        if check_file_exists(doc, project_root):
            print(f"  ✅ {doc}")
        else:
            errors.append(f"  ❌ 缺少 Output Parser 文档: {doc}")
    
    # 6. 检查文档中的代码示例语法
    print("\n6. 检查文档中的代码块...")
    doc_files = list((project_root / "docs").rglob("*.md"))
    doc_files.append(project_root / "README.md")
    
    code_block_pattern = r'```(\w+)?\n(.*?)```'
    for doc_file in doc_files:
        if doc_file.exists():
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            code_blocks = re.findall(code_block_pattern, content, re.DOTALL)
            if code_blocks:
                print(f"  ✅ {doc_file.relative_to(project_root)}: {len(code_blocks)} 个代码块")
    
    # 输出结果
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    
    if errors:
        print(f"\n❌ 发现 {len(errors)} 个错误:")
        for error in errors:
            print(error)
    
    if warnings:
        print(f"\n⚠️  发现 {len(warnings)} 个警告:")
        for warning in warnings:
            print(warning)
    
    if not errors and not warnings:
        print("\n✅ 所有检查通过！文档一致性良好。")
        return 0
    elif not errors:
        print("\n✅ 没有发现错误，但有一些警告需要注意。")
        return 0
    else:
        print(f"\n❌ 验证失败，请修复上述错误。")
        return 1

if __name__ == "__main__":
    exit(validate_documentation())
