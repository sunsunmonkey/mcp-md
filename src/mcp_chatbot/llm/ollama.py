"""Ollama LLM 客户端"""

import os
from typing import Optional

import dotenv
import requests

dotenv.load_dotenv()


class OllamaClient:
    """Ollama LLM 客户端"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        self.model_name = model_name or os.getenv("OLLAMA_MODEL_NAME", "gemma:2b")
        self.api_base = api_base or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def get_response(self, messages: list[dict[str, str]]) -> str:
        """获取 LLM 响应
        
        Args:
            messages: 消息列表
            
        Returns:
            LLM 响应内容
        """
        response = requests.post(
            f"{self.api_base}/api/chat",
            json={
                "model": self.model_name,
                "messages": messages,
                "stream": False,
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def get_stream_response(self, messages: list[dict[str, str]]):
        """获取流式 LLM 响应
        
        Args:
            messages: 消息列表
            
        Yields:
            响应片段
        """
        response = requests.post(
            f"{self.api_base}/api/chat",
            json={
                "model": self.model_name,
                "messages": messages,
                "stream": True,
            },
            stream=True,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                data = line.decode("utf-8")
                if data == '{"done":true}':
                    continue

                import json
                try:
                    chunk = json.loads(data)
                    if "message" in chunk and "content" in chunk["message"]:
                        content = chunk["message"]["content"]
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue
