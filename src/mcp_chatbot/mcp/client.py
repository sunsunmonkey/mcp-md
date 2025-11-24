"""MCP 客户端实现"""

import asyncio
import logging
import os
import shutil
from contextlib import AsyncExitStack
from typing import Any, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .mcp_tool import MCPTool


class MCPClient:
    """MCP 客户端，管理与 MCP 服务器的连接"""

    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name: str = name
        self.config: dict[str, Any] = config
        self.session: ClientSession | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        """初始化服务器连接"""
        command = (
            shutil.which("npx")
            if self.config["command"] == "npx"
            else self.config["command"]
        )
        if command is None:
            raise ValueError("命令必须是有效的字符串")

        server_params = StdioServerParameters(
            command=command,
            args=self.config["args"],
            env={**os.environ, **self.config["env"]}
            if self.config.get("env")
            else None,
        )
        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
        except Exception as e:
            logging.error(f"初始化服务器 {self.name} 时出错: {e}")
            await self.cleanup()
            raise

    async def list_tools(self) -> List[MCPTool]:
        """列出可用工具
        
        Returns:
            可用工具列表
        """
        if not self.session:
            raise RuntimeError(f"服务器 {self.name} 未初始化")

        tools_response = await self.session.list_tools()
        tools = []

        for item in tools_response:
            if isinstance(item, tuple) and item[0] == "tools":
                for tool in item[1]:
                    tools.append(MCPTool(tool.name, tool.description, tool.inputSchema))
        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 2,
        delay: float = 1.0,
    ) -> Any:
        """执行工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            retries: 重试次数
            delay: 重试延迟（秒）
            
        Returns:
            工具执行结果
        """
        if not self.session:
            raise RuntimeError(f"服务器 {self.name} 未初始化")

        attempt = 0
        while attempt < retries:
            try:
                logging.info(f"执行 {tool_name}...")
                result = await self.session.call_tool(tool_name, arguments)
                return result

            except Exception as e:
                attempt += 1
                logging.warning(
                    f"执行工具时出错: {e}. 尝试 {attempt}/{retries}."
                )
                if attempt < retries:
                    logging.info(f"{delay} 秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    logging.error("达到最大重试次数")
                    raise

    async def cleanup(self) -> None:
        """清理资源"""
        async with self._cleanup_lock:
            try:
                await self.exit_stack.aclose()
                self.session = None
            except Exception as e:
                logging.error(f"清理服务器 {self.name} 时出错: {e}")

    async def __aenter__(self):
        """进入异步上下文"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出异步上下文"""
        await self.cleanup()
