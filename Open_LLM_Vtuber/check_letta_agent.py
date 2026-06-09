import httpx

# Letta 服务器地址
LETA_SERVER_URL = "http://localhost:9000"

async def check_agents():
    """检查所有 Letta agents 的配置"""
    async with httpx.AsyncClient() as client:
        try:
            # 获取所有 agents
            response = await client.get(f"{LETA_SERVER_URL}/v1/agents/")
            response.raise_for_status()
            agents = response.json()
            
            print("=== Letta Agents 配置 ===")
            for agent in agents:
                print(f"\nAgent ID: {agent['id']}")
                print(f"Name: {agent.get('name', 'N/A')}")
                print(f"Created: {agent.get('created_at', 'N/A')}")
                
                # 获取 agent 详情
                agent_id = agent['id']
                detail_response = await client.get(f"{LETA_SERVER_URL}/v1/agents/{agent_id}")
                detail_response.raise_for_status()
                agent_detail = detail_response.json()
                
                # 打印 LLM 配置
                print("\n=== LLM 配置 ===")
                llm_config = agent_detail.get('llm_config', {})
                if llm_config:
                    print(f"Provider: {llm_config.get('provider', 'N/A')}")
                    print(f"Model: {llm_config.get('model', 'N/A')}")
                    print(f"Base URL: {llm_config.get('base_url', 'N/A')}")
                else:
                    print("No LLM config found!")
                
                # 打印嵌入配置
                print("\n=== Embedding 配置 ===")
                embedding_config = agent_detail.get('embedding_config', {})
                if embedding_config:
                    print(f"Provider: {embedding_config.get('provider', 'N/A')}")
                    print(f"Model: {embedding_config.get('model', 'N/A')}")
                    print(f"Base URL: {embedding_config.get('base_url', 'N/A')}")
                else:
                    print("No embedding config found!")
                    
        except httpx.RequestError as e:
            print(f"连接错误: {e}")
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_agents())
