"""终端聊天机器人 - 主入口"""

import asyncio
import logging
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from mcp_chatbot import ChatSession, Configuration, OllamaClient, SiliconFlowClient, MCPClient
import os


async def main() -> None:
    """主函数"""
    # 加载配置
    config = Configuration()
    
    # 根据环境变量选择 LLM 提供商
    llm_provider = os.getenv("LLM_PROVIDER", "ollama")
    
    if llm_provider == "siliconflow":
        llm_client = SiliconFlowClient()
        print(f"使用硅基流动模型: {llm_client.model_name}")
    else:
        llm_client = OllamaClient(
            model_name=config.ollama_model_name,
            api_base=config.ollama_base_url,
        )
        print(f"使用 Ollama 模型: {llm_client.model_name}")
    
    # 创建 MCP 客户端
    clients = []
    
    # 加载 MCP 服务器配置
    try:
        server_config = config.load_config("mcp_servers/servers_config.json")
        for name, srv_config in server_config["mcpServers"].items():
            if not srv_config.get("isActive", True):
                continue
            
            # 只支持 stdio 类型的 MCP 客户端
            clients.append(MCPClient(name, srv_config))
    except FileNotFoundError:
        logging.warning("未找到 MCP 服务器配置文件，将不使用 MCP 工具")
    except Exception as e:
        logging.error(f"加载 MCP 配置失败: {e}")
    
    # 创建聊天会话
    chat_session = ChatSession(clients, llm_client)
    
    # 初始化会话
    init_success = await chat_session.initialize()
    if not init_success:
        logging.error("初始化聊天会话失败")
        return
    
    print("=" * 50)
    print("MCP-MD Agent")
    print("=" * 50)
    print(f"MCP 工具: {len(clients)} 个服务器")
    print("命令: quit/exit 退出, clear 清空历史")
    print()
    
    try:
        # 主聊天循环
        while True:
            try:
                # 获取用户输入
                user_input = input("You: ").strip()
                
                # 检查退出命令
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n再见！")
                    break
                
                # 清空历史
                if user_input.lower() == "clear":
                    chat_session.clear_history()
                    print("对话历史已清空\n")
                    continue
                
                if not user_input:
                    continue
                
                # 处理消息并获取响应
                response = await chat_session.send_message(user_input)
                
                # 显示响应
                print(f"\nAssistant: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\n再见！")
                break
    finally:
        # 清理资源
        await chat_session.cleanup_clients()


if __name__ == "__main__":
    asyncio.run(main())
