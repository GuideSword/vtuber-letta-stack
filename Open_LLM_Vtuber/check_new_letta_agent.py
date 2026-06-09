import httpx

# Letta 服务器地址
LETA_SERVER_URL = "http://localhost:9000"
# 新创建的代理ID
AGENT_ID = "agent-64c65522-f3e5-475e-9a5a-7786a8c669bf"

async def check_agent_config():
    """检查新创建的Letta代理配置"""
    async with httpx.AsyncClient() as client:
        try:
            # 获取代理详情
            response = await client.get(f"{LETA_SERVER_URL}/v1/agents/{AGENT_ID}")
            response.raise_for_status()
            agent_detail = response.json()
            
            print("=== 新Letta代理配置详情 ===")
            print(f"Agent ID: {agent_detail['id']}")
            print(f"Name: {agent_detail.get('name', 'N/A')}")
            print(f"Created: {agent_detail.get('created_at', 'N/A')}")
            
            # 打印LLM配置
            print("\n=== LLM 配置 ===")
            llm_config = agent_detail.get('llm_config', {})
            if llm_config:
                print(f"Provider: {llm_config.get('provider', 'N/A')}")
                print(f"Model: {llm_config.get('model', 'N/A')}")
                print(f"Base URL: {llm_config.get('base_url', 'N/A')}")
                print(f"Model Endpoint: {llm_config.get('model_endpoint', 'N/A')}")
                print(f"Model Endpoint Type: {llm_config.get('model_endpoint_type', 'N/A')}")
                print(f"API Key: {llm_config.get('api_key', 'N/A')}")
                print(f"Context Window: {llm_config.get('context_window', 'N/A')}")
                print(f"Temperature: {llm_config.get('temperature', 'N/A')}")
            else:
                print("No LLM config found!")
            
            # 打印嵌入配置
            print("\n=== Embedding 配置 ===")
            embedding_config = agent_detail.get('embedding_config', {})
            if embedding_config:
                print(f"Provider: {embedding_config.get('provider', 'N/A')}")
                print(f"Model: {embedding_config.get('model', 'N/A')}")
                print(f"Embedding Model: {embedding_config.get('embedding_model', 'N/A')}")
                print(f"Base URL: {embedding_config.get('base_url', 'N/A')}")
                print(f"Embedding Endpoint Type: {embedding_config.get('embedding_endpoint_type', 'N/A')}")
                print(f"API Key: {embedding_config.get('api_key', 'N/A')}")
                print(f"Embedding Dim: {embedding_config.get('embedding_dim', 'N/A')}")
            else:
                print("No embedding config found!")
                
        except httpx.RequestError as e:
            print(f"连接错误: {e}")
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_agent_config())
