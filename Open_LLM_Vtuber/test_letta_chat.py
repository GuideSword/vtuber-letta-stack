from src.open_llm_vtuber.agent.agents.letta_agent import LettaAgent
from src.open_llm_vtuber.agent.input_types import BatchInput, TextData, TextSource
import asyncio

# 创建一个简单的LettaAgent实例用于测试
class MockLive2DModel:
    def __init__(self):
        pass

# 创建LettaAgent实例
agent = LettaAgent(
    live2d_model=MockLive2DModel(),
    id="agent-7b8b265e-2a67-4241-a6e5-449f369d773b",
    host="localhost",
    port=9000
)

# 创建测试输入数据
async def test_chat():
    print("Testing LettaAgent chat...")
    print("=" * 50)
    
    # 创建输入数据
    input_data = BatchInput(
        texts=[
            TextData(
                content="你好，能听到我说话吗？",
                source=TextSource.INPUT
            )
        ],
        images=[],
        context={}
    )
    
    print(f"Sending input: {input_data.texts[0].content}")
    print("=" * 50)
    
    try:
        # 测试聊天功能
        response = []
        async for token in agent.chat(input_data):
            print(f"Received token: {token}")
            response.append(token)
        
        complete_response = "".join(response)
        print("=" * 50)
        print(f"Complete response: {complete_response}")
        print("=" * 50)
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_chat())
