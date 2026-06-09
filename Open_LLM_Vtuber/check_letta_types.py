from letta_client import Letta
import sys

# 检查Letta客户端库的类型定义
print("Checking Letta client types...")
print("=" * 50)

try:
    from letta_client.types import *
    print("Available types in letta_client.types:")
    for name in dir():
        if not name.startswith('_'):
            print(f"  - {name}")
    print("=" * 50)
    
    # 特别检查消息类型
    print("Message-related types:")
    message_types = []
    for name in dir():
        if 'message' in name.lower() and not name.startswith('_'):
            message_types.append(name)
            print(f"  - {name}")
    print("=" * 50)
    
    # 检查AssistantMessage类型（如果存在）
    if 'AssistantMessage' in dir():
        from letta_client.types.assistant_message import AssistantMessage
        print("AssistantMessage attributes:")
        print(f"  {dir(AssistantMessage)}")
    else:
        print("AssistantMessage type not found!")
    print("=" * 50)
    
    # 检查其他可能的消息类型
    for msg_type in message_types:
        if msg_type != 'AssistantMessage':
            print(f"Checking {msg_type}:")
            try:
                cls = getattr(sys.modules['letta_client.types'], msg_type)
                print(f"  Attributes: {dir(cls)}")
            except:
                pass
            print("-" * 30)
            
    print("=" * 50)
    print("Type check completed")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
