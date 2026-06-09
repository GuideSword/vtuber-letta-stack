import requests
import json

# 测试Open_LLM_Vtuber的TTS功能
def test_ollm_tts():
    url = "http://localhost:12394/api/tts"
    
    # 构造请求数据
    data = {
        "text": "测试文本，这是一个测试。",
        "model": "gpt_sovits_tts"
    }
    
    print("测试Open_LLM_Vtuber的TTS功能...")
    print(f"请求URL: {url}")
    print(f"请求数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        # 发送POST请求
        response = requests.post(url, json=data, timeout=30)
        
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容长度: {len(response.content)} 字节")
        print(f"响应内容类型: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            # 保存响应内容到文件
            with open("ollm_test_output.wav", "wb") as f:
                f.write(response.content)
            print("\n测试成功！音频已保存到 ollm_test_output.wav")
        else:
            print(f"\n测试失败！响应内容: {response.text}")
    except Exception as e:
        print(f"\n测试异常: {e}")

if __name__ == "__main__":
    test_ollm_tts()
