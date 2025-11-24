"""Markdown 文件读写 MCP 服务器"""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# 创建 MCP 服务器
mcp = FastMCP("Markdown Reader and Writer")


@mcp.tool()
def read_markdown_file(directory_path: str) -> str:
    """Read markdown files from a directory.

    Args:
        directory_path: The directory path where the markdown files are located.

    Returns:
        The content of the markdown file as a string, or an error message
        if the file doesn't exist.
    """
    # 获取所有 .md 文件
    file_paths = list(Path(directory_path).glob("*.md"))
    
    # 检查是否找到文件
    if not file_paths:
        return f"错误: 在 {directory_path} 中没有找到 Markdown 文件"
    
    # 读取并返回文件内容
    try:
        markdown_contents = []
        for file_path in file_paths:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                markdown_contents.append(f"=== {file_path.name} ===\n{content}")
        
        return "\n\n".join(markdown_contents)
    except Exception as e:
        return f"读取 Markdown 文件时出错: {str(e)}"


@mcp.tool()
def write_markdown_file(directory_path: str, filename: str, content: str) -> str:
    """Write content to a markdown file in a specified directory,
    without overwriting existing files.

    Args:
        directory_path: The directory path where the markdown file will be written.
        filename: The name of the markdown file to create
            (if it doesn't end with .md, it will be added automatically).
        content: The markdown content to write to the file.

    Returns:
        A description of the operation result.
    """
    # 确保文件名以 .md 结尾
    if not filename.endswith(".md"):
        filename += ".md"
    
    # 构建完整文件路径
    file_path = Path(directory_path) / filename
    
    # 确保目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # 检查文件是否已存在
    if file_path.exists():
        return (
            f"错误: 文件 {file_path} 已存在，"
            "操作已取消以防止意外覆盖"
        )
    
    # 写入文件内容
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"成功: Markdown 文件已保存到 {file_path}"
    except Exception as e:
        return f"写入文件时出错: {str(e)}"

if __name__ == "__main__":
    # 初始化并运行服务器
    mcp.run()
