"""硅基流动 LLM 客户端"""

import os
from typing import Optional

import dotenv
import requests

dotenv.load_dotenv()


class SiliconFlowClient:
    """硅基流动 LLM 客户端（OpenAI 兼容）"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model_name = model_name or os.getenv("SILICONFLOW_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.base_url = base_url or os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
        
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY not found in environment variables")

    def get_response(self, messages: list[dict[str, str]]) -> str:
        """获取 LLM 响应
        
        Args:
            messages: 消息列表
            
        Returns:
            LLM 响应内容
        """
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model_name,
                "messages": messages,
                "stream": False,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def get_stream_response(self, messages: list[dict[str, str]]):
        """获取流式 LLM 响应
        
        Args:
            messages: 消息列表
            
        Yields:
            响应片段
        """
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
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
                if data.startswith("data: "):
                    data = data[6:]
                    
                if data.strip() == "[DONE]":
                    continue

                import json
                try:
                    chunk = json.loads(data)
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue
