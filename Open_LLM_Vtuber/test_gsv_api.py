import requests
import json

# 测试GPT-Sovits API
def test_gsv_api():
    url = "http://127.0.0.1:12345/"
    
    # 构造请求数据，使用GPT-Sovits API期望的参数名称
    data = {
        "text": "测试文本",
        "text_language": "zh",
        "refer_wav_path": "models/tmp/003.wav",
        "prompt_language": "zh",
        "prompt_text": "你好，我是小c，很高兴认识你。",
        "top_k": 15
    }
    
    print("测试GPT-Sovits API...")
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
            with open("test_output.wav", "wb") as f:
                f.write(response.content)
            print("\n测试成功！音频已保存到 test_output.wav")
        else:
            print(f"\n测试失败！响应内容: {response.text}")
    except Exception as e:
        print(f"\n测试异常: {e}")

if __name__ == "__main__":
    test_gsv_api()
