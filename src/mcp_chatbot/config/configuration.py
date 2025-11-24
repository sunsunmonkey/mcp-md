"""配置管理"""

import json
import os
from typing import Any, Optional

import dotenv


class Configuration:
    """管理配置和环境变量"""

    def __init__(self) -> None:
        """初始化配置"""
        self.load_env()
        self._ollama_model_name = os.getenv("OLLAMA_MODEL_NAME")
        self._ollama_base_url = os.getenv("OLLAMA_BASE_URL")

    @staticmethod
    def load_env() -> None:
        """加载环境变量"""
        dotenv.load_dotenv()

    @staticmethod
    def load_config(file_path: str) -> dict[str, Any]:
        """加载 JSON 配置文件
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            配置字典
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def ollama_model_name(self) -> str:
        """获取 Ollama 模型名称"""
        if not self._ollama_model_name:
            raise ValueError("OLLAMA_MODEL_NAME not found in environment variables")
        return self._ollama_model_name

    @property
    def ollama_base_url(self) -> str:
        """获取 Ollama base URL"""
        if not self._ollama_base_url:
            return "http://localhost:11434"
        return self._ollama_base_url
