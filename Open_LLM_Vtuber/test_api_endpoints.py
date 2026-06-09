import requests
import json

# 测试多个可能的API端点
def test_api_endpoints():
    base_url = "http://127.0.0.1:12345"
    endpoints = ["", "/", "/tts", "/api/tts"]
    
    # 构造请求数据，使用正确的参数名称
    data = {
        "text": "测试文本",
        "text_lang": "zh",
        "ref_audio_path": "models/tmp/003.wav",
        "prompt_lang": "zh",
        "prompt_text": "你好，我是小c，很高兴认识你。",
        "top_k": 15
    }
    
    print("测试多个API端点...")
    
    for endpoint in endpoints:
        url = base_url + endpoint
        print(f"\n测试端点: {url}")
        
        try:
            # 发送POST请求
            response = requests.post(url, json=data, timeout=10)
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                print("✓ 测试成功！")
                # 保存响应内容到文件
                with open(f"test_output_{endpoint.replace('/', '_')}.wav", "wb") as f:
                    f.write(response.content)
                print(f"音频已保存到 test_output_{endpoint.replace('/', '_')}.wav")
            else:
                print("✗ 测试失败！")
        except Exception as e:
            print(f"✗ 测试异常: {e}")

if __name__ == "__main__":
    test_api_endpoints()
