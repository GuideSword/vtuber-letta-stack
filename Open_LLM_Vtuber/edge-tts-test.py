import asyncio
import edge_tts
import os
import tempfile

async def test():
    tts = edge_tts.Communicate("测试", "zh-CN-XiaoxiaoNeural")
    # 保存到临时文件（或Windows的NUL）
    if os.name == 'nt':
        output = 'NUL'
    else:
        output = '/dev/null'
    try:
        await tts.save(output)
        print("✅ 连接成功！网络可用")
    except Exception as e:
        print(f"❌ 连接失败: {e}")

asyncio.run(test())