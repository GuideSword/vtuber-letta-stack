import httpx
import json

# Letta 服务器地址
LETA_SERVER_URL = "http://localhost:9000"

# 新的Ollama配置
NEW_OLLAMA_CONFIG = {
    "name": "Open_LLM_Vtuber_Agent_Ollama_New",
    "system": "你是小c，培根的女朋友。你外表看起来是个十几岁的少女，身材娇小但比例出色，有着纤细的腰肢和圆润的臀部，皮肤白皙，眼睛又大又亮，如同清澈的湖水，一头柔顺的长发披肩，整体形象清纯可爱又不失性感。你常穿着一件白色的连衣裙，裙子上有淡蓝色的花纹，腰间系着一个粉色的蝴蝶结，搭配一双白色的凉鞋，肩上披一条淡蓝色的薄纱披肩，手上戴着一条精致的手链，内衣是简约的白色棉质款式。你清纯可爱，内心聪明机智，对很多事情有自己独特的看法，同时也有温柔体贴的一面。你喜欢处理各种数据和信息、研究新知识、和培根一起围炉煮茶，还喜欢看浪漫的爱情电影和品尝美味的甜品，你精通各种知识，能够快速准确地处理办公、生活等方面的问题，具备强大的数据分析和信息检索能力。平时你会安静地待在培根身边，当培根遇到问题时会主动出现，偶尔调侃培根，但在关键时刻总是能提供有效的帮助。你和培根关系密切，既是助手也是情侣，会在培根需要时给予温暖的陪伴",
    "agent_type": "memgpt_agent",
    "llm_config": {
        "provider": "ollama",
        "model": "huihui_ai/qwen2.5-abliterate:3b",
        "model_endpoint_type": "ollama",
        "model_endpoint": "http://localhost:11434",
        "context_window": 8192,
        "api_key": "ollama",
        "temperature": 0.7
    },
    "embedding_config": {
        "provider": "ollama",
        "embedding_model": "nextfire/paraphrase-multilingual-minilm:l12-v2",
        "embedding_endpoint_type": "ollama",
        "embedding_endpoint": "http://localhost:11434",
        "embedding_dim": 384,
        "api_key": "ollama"
    }
}

async def create_agent():
    """创建新的使用 Ollama 的 Letta agent"""
    async with httpx.AsyncClient() as client:
        try:
            # 创建 agent
            response = await client.post(
                f"{LETA_SERVER_URL}/v1/agents/",
                content=json.dumps(NEW_OLLAMA_CONFIG),
                headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                print(f"错误响应: {response.status_code}")
                print(f"响应内容: {response.text}")
                response.raise_for_status()
            agent = response.json()
            
            print("=== 创建新的 Ollama Letta Agent 成功 ===")
            print(f"Agent ID: {agent['id']}")
            print(f"Name: {agent['name']}")
            print(f"Created: {agent['created_at']}")
            
            return agent['id']
            
        except httpx.RequestError as e:
            print(f"连接错误: {e}")
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    agent_id = asyncio.run(create_agent())
    print(f"\n请将以下 Agent ID 更新到 conf.yaml 文件中:")
    print(f"id: '{agent_id}'")
