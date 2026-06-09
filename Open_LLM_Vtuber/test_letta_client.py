from letta_client import Letta
import sys

# 创建Letta客户端
client = Letta(base_url="http://localhost:9000")
agent_id = "agent-7b8b265e-2a67-4241-a6e5-449f369d773b"

print(f"Testing Letta client with agent: {agent_id}")
print("=" * 50)

# 测试发送消息
messages = [{"role": "user", "content": "你好，能听到我说话吗？"}]

print(f"Sending message: {messages}")
print("=" * 50)

try:
    # 创建流式响应
    stream = client.agents.messages.create_stream(
        agent_id=agent_id,
        messages=messages,
        stream_tokens=True,
    )
    
    print("Receiving stream...")
    print("=" * 50)
    
    # 遍历流式响应
    for i, token in enumerate(stream):
        print(f"Token #{i}:")
        print(f"  Type: {type(token)}")
        print(f"  Token: {token}")
        
        # 检查token的属性
        print(f"  Attributes: {dir(token)}")
        
        if hasattr(token, 'message_type'):
            print(f"  Message type: {token.message_type}")
        
        if hasattr(token, 'content'):
            print(f"  Content: {token.content}")
        
        if hasattr(token, 'reasoning'):
            print(f"  Reasoning: {token.reasoning}")
        
        print("-" * 30)
        
        # 只显示前20个token以避免输出过多
        if i >= 19:
            print("... (truncated)")
            break
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 50)
print("Test completed")
