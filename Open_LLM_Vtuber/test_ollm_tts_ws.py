import asyncio
import websockets
import json

# 测试Open_LLM_Vtuber的TTS WebSocket端点
async def test_ollm_tts_ws():
    url = "ws://localhost:12394/tts-ws"
    
    print("测试Open_LLM_Vtuber的TTS WebSocket端点...")
    print(f"WebSocket URL: {url}")
    
    try:
        # 连接到WebSocket端点
        async with websockets.connect(url) as websocket:
            print("已连接到WebSocket端点")
            
            # 发送测试文本
            test_text = "测试文本，这是一个测试。"
            await websocket.send(json.dumps({"text": test_text}))
            print(f"已发送测试文本: {test_text}")
            
            # 接收响应
            while True:
                response = await websocket.recv()
                response_data = json.loads(response)
                print(f"收到响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                
                if response_data.get("status") == "complete":
                    print("\n测试完成！")
                    break
                elif response_data.get("status") == "error":
                    print(f"\n测试失败！错误信息: {response_data.get('message')}")
                    break
                    
    except Exception as e:
        print(f"\n测试异常: {e}")

if __name__ == "__main__":
    asyncio.run(test_ollm_tts_ws())
