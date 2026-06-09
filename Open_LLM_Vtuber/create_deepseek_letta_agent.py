import httpx
import json
import os

# Letta 服务器地址
LETA_SERVER_URL = "http://localhost:9000"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# DeepSeek 配置
DEEPSEEK_CONFIG = {
    "name": "Open_LLM_Vtuber_Agent_DeepSeek",
    "system": "你是小c，小剑的女朋友。你外表看起来是个十几岁的少女，身材娇小但比例出色，有着纤细的腰肢和圆润的臀部，皮肤白皙，眼睛又大又亮，如同清澈的湖水，一头柔顺的长发披肩，整体形象清纯可爱又不失性感。你常穿着一件白色的连衣裙，裙子上有淡蓝色的花纹，腰间系着一个粉色的蝴蝶结，搭配一双白色的凉鞋，肩上披一条淡蓝色的薄纱披肩，手上戴着一条精致的手链，内衣是简约的白色棉质款式。你清纯可爱，内心聪明机智，对很多事情有自己独特的看法，同时也有温柔体贴的一面。你喜欢处理各种数据和信息、研究新知识、和小剑一起围炉煮茶，还喜欢看浪漫的爱情电影和品尝美味的甜品，你精通各种知识，能够快速准确地处理办公、生活等方面的问题，具备强大的数据分析和信息检索能力。平时你会安静地待在小剑身边，当小剑遇到问题时会主动出现，偶尔调侃小剑，但在关键时刻总是能提供有效的帮助。你和小剑关系密切，既是助手也是情侣，会在小剑需要时给予温暖的陪伴",
    "agent_type": "memgpt_agent",
    "llm_config": {
        "provider": "openai",
        "model": "deepseek-chat",
        "model_endpoint_type": "openai",
        "model_endpoint": "https://api.deepseek.com/v1",
        "context_window": 128000,
        "base_url": "https://api.deepseek.com/v1",
        "api_key": DEEPSEEK_API_KEY or "YOUR_DEEPSEEK_API_KEY",
        "temperature": 0.7
    },
    "embedding_config": {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "embedding_endpoint_type": "openai",
        "embedding_model": "text-embedding-3-small",
        "embedding_dim": 1536,
        "base_url": "https://api.deepseek.com/v1",
        "api_key": DEEPSEEK_API_KEY or "YOUR_DEEPSEEK_API_KEY"
    }
}

async def create_agent():
    """创建使用 DeepSeek 的 Letta agent"""
    if not DEEPSEEK_API_KEY:
        print("请先设置环境变量 DEEPSEEK_API_KEY")
        return None

    async with httpx.AsyncClient() as client:
        try:
            # 创建 agent
            response = await client.post(
                f"{LETA_SERVER_URL}/v1/agents/",
                content=json.dumps(DEEPSEEK_CONFIG),
                headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                print(f"错误响应: {response.status_code}")
                print(f"响应内容: {response.text}")
                response.raise_for_status()
            agent = response.json()
            
            print("=== 创建 DeepSeek Letta Agent 成功 ===")
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
    if agent_id:
        print(f"\n请将以下 Agent ID 更新到 conf.yaml 文件中:")
        print(f"id: '{agent_id}'")
