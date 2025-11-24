"""聊天会话管理"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..llm.ollama import OllamaClient
from ..mcp import MCPClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

SYSTEM_MESSAGE = (
    "You are a helpful assistant with access to these tools:\n\n"
    "{tools_description}\n\n"
    "Choose the appropriate tool based on the user's question. "
    "If no tool is needed, reply directly.\n\n"
    "IMPORTANT: When you need to use a tool, you must respond with "
    "the exact JSON object format below:\n"
    "{{\n"
    '    "tool": "tool-name",\n'
    '    "arguments": {{\n'
    '        "argument-name": "value"\n'
    "    }}\n"
    "}}\n\n"
    "After receiving tool responses:\n"
    "1. Transform the raw data into a natural, conversational response\n"
    "2. Keep responses concise but informative\n"
    "3. Focus on the most relevant information\n"
    "4. Use appropriate context from the user's question\n"
    "5. Answer my question in Chinese\n"
    "6. Avoid simply repeating the raw data\n\n"
    "Please use only the tools that are explicitly defined above."
)


@dataclass
class ToolCall:
    """工具调用数据结构"""

    tool: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None

    def is_successful(self) -> bool:
        """检查工具调用是否成功"""
        return self.error is None and self.result is not None


class ChatSession:
    """管理聊天会话"""

    def __init__(self, clients: List[MCPClient], llm_client: OllamaClient) -> None:
        """初始化聊天会话
        
        Args:
            clients: MCP 客户端列表
            llm_client: LLM 客户端
        """
        self.clients: List[MCPClient] = clients
        self.llm_client: OllamaClient = llm_client
        self.messages: List[Dict[str, str]] = []
        self._is_initialized: bool = False

    async def cleanup_clients(self) -> None:
        """清理所有客户端资源"""
        for client in self.clients:
            try:
                await client.cleanup()
            except Exception as e:
                logging.warning(f"清理客户端 {client.name} 时警告: {e}")

    async def initialize(self) -> bool:
        """初始化 MCP 客户端并准备系统消息
        
        Returns:
            初始化是否成功
        """
        try:
            if self._is_initialized:
                return True

            # 初始化所有 MCP 客户端
            self.tool_client_map = {}
            for client in self.clients:
                try:
                    await client.initialize()
                    tools = await client.list_tools()
                    for tool in tools:
                        if tool.name in self.tool_client_map:
                            logging.warning(
                                f"工具 {tool.name} 已存在于 "
                                f"{self.tool_client_map[tool.name].name}"
                            )
                        self.tool_client_map[tool.name] = client
                except Exception as e:
                    logging.error(f"初始化客户端失败: {e}")
                    await self.cleanup_clients()
                    return False

            # 收集所有可用工具
            all_tools = []
            for client in self.clients:
                tools = await client.list_tools()
                all_tools.extend(tools)

            # 格式化工具描述并创建系统消息
            tools_description = "\n".join([tool.format_for_llm() for tool in all_tools])
            system_message = SYSTEM_MESSAGE.format(tools_description=tools_description)

            self.messages = [{"role": "system", "content": system_message}]
            self._is_initialized = True
            return True
        except Exception as e:
            logging.error(f"初始化错误: {e}")
            await self.cleanup_clients()
            return False

    def _extract_tool_calls(self, llm_response: str) -> List[Dict[str, Any]]:
        """从 LLM 响应中提取工具调用
        
        Args:
            llm_response: LLM 响应文本
            
        Returns:
            提取的工具调用列表
        """
        # 尝试解析整个响应为 JSON
        try:
            tool_call = json.loads(llm_response)
            if (
                isinstance(tool_call, dict)
                and "tool" in tool_call
                and "arguments" in tool_call
            ):
                return [tool_call]
        except json.JSONDecodeError:
            pass

        # 尝试从响应中提取所有 JSON 对象
        tool_calls = []
        json_pattern = r"({[^{}]*({[^{}]*})*[^{}]*})"
        json_matches = re.finditer(json_pattern, llm_response)

        for match in json_matches:
            try:
                json_obj = json.loads(match.group(0))
                if (
                    isinstance(json_obj, dict)
                    and "tool" in json_obj
                    and "arguments" in json_obj
                ):
                    tool_calls.append(json_obj)
            except json.JSONDecodeError:
                continue

        return tool_calls

    async def _execute_tool_call(self, tool_call_data: Dict[str, Any]) -> ToolCall:
        """执行单个工具调用
        
        Args:
            tool_call_data: 工具调用数据
            
        Returns:
            工具调用结果
        """
        tool_name = tool_call_data["tool"]
        arguments = tool_call_data["arguments"]

        tool_call = ToolCall(tool=tool_name, arguments=arguments)
        
        # 显示工具调用信息

        args_str = json.dumps(arguments, ensure_ascii=False, indent=2)
        print(f"\n🔧 调用工具: {tool_name}")
        print(f"📝 参数: {args_str}")

        # 从工具客户端映射中查找客户端
        if tool_name in self.tool_client_map:
            client = self.tool_client_map[tool_name]
            try:
                result = await client.execute_tool(tool_name, arguments)
                tool_call.result = result
                print(f"✅ 执行成功\n")
                return tool_call
            except Exception as e:
                error_msg = f"执行工具时出错: {str(e)}"
                logging.error(error_msg)
                tool_call.error = error_msg
                print(f"❌ 执行失败: {error_msg}\n")
                return tool_call

        # 未找到可执行此工具的客户端
        tool_call.error = f"未找到工具: {tool_name}"
        print(f"❌ 未找到工具\n")
        return tool_call

    async def process_tool_calls(self, llm_response: str) -> Tuple[List[ToolCall], bool]:
        """处理工具调用
        
        Args:
            llm_response: LLM 响应
            
        Returns:
            (工具调用列表, 是否有工具调用)
        """
        tool_call_data_list = self._extract_tool_calls(llm_response)
        
        if not tool_call_data_list:
            return [], False
        
        tool_calls = []
        for tool_call_data in tool_call_data_list:
            tool_call = await self._execute_tool_call(tool_call_data)
            tool_calls.append(tool_call)
        
        return tool_calls, True

    async def send_message(self, user_message: str, max_iterations: int = 5) -> str:
        """发送消息并获取响应，自动处理工具调用迭代
        
        Args:
            user_message: 用户消息
            max_iterations: 最大工具调用迭代次数
            
        Returns:
            最终响应文本
        """
        if not self._is_initialized:
            success = await self.initialize()
            if not success:
                return "初始化聊天会话失败"

        # 添加用户消息
        self.messages.append({"role": "user", "content": user_message})

        # 获取初始 LLM 响应
        llm_response = self.llm_client.get_response(self.messages)
        self.messages.append({"role": "assistant", "content": llm_response})

        # 自动处理工具调用迭代
        tool_iteration = 0
        while tool_iteration < max_iterations:
            tool_iteration += 1
            
            # 处理工具调用
            tool_calls, has_tools = await self.process_tool_calls(llm_response)
            
            if not has_tools:
                # 没有工具调用，返回最终响应
                return llm_response
            
            # 格式化工具结果
            tool_results = "\n\n".join(
                [
                    f"工具: {tc.tool}\n参数: {json.dumps(tc.arguments, ensure_ascii=False)}\n"
                    f"结果: {tc.result if tc.is_successful() else tc.error}"
                    for tc in tool_calls
                ]
            )
            
            # 将工具结果添加到消息历史
            self.messages.append({"role": "system", "content": f"工具执行结果:\n\n{tool_results}"})
            
            # 获取下一个 LLM 响应
            llm_response = self.llm_client.get_response(self.messages)
            self.messages.append({"role": "assistant", "content": llm_response})
            
            # 检查下一个响应是否还包含工具调用
            next_tool_calls = self._extract_tool_calls(llm_response)
            if not next_tool_calls:
                # 没有更多工具调用，返回最终响应
                return llm_response
        
        # 达到最大迭代次数
        logging.warning(f"达到最大工具调用迭代次数 ({max_iterations})")
        return llm_response

    def clear_history(self) -> None:
        """清空对话历史"""
        if self._is_initialized and self.messages:
            # 保留系统消息
            system_message = self.messages[0]
            self.messages = [system_message]
