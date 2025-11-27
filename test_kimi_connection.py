#!/usr/bin/env python3
"""
测试 Kimi API 连接
"""
import os
from openai import OpenAI

def test_connection():
    """测试 Kimi API 连接"""
    
    # 获取 API Key
    api_key = os.getenv("MOONSHOT_API_KEY")
    
    if not api_key:
        print("❌ 错误: 未设置 MOONSHOT_API_KEY 环境变量")
        print("\n请运行:")
        print('export MOONSHOT_API_KEY="sk-Mt7Mh7krVbANT1qm9bBExcZBgqL3VeOKeIkooUlYex1iI4Gu"')
        return False
    
    print(f"✅ API Key 已设置: {api_key[:20]}...")
    print(f"🔗 连接到: https://api.moonshot.cn/v1")
    
    # 初始化客户端
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1"
    )
    
    try:
        print("\n📡 正在测试连接...")
        
        # 发起简单的聊天请求
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[
                {"role": "system", "content": "你是一个助手。"},
                {"role": "user", "content": "请用一句话介绍你自己。"}
            ],
            temperature=0.0,
            max_tokens=100
        )
        
        # 输出结果
        content = response.choices[0].message.content
        print(f"\n✅ 连接成功！")
        print(f"🤖 Kimi 回复: {content}")
        print(f"\n📊 模型: {response.model}")
        print(f"📊 使用 tokens: {response.usage.total_tokens}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        print("\n可能的原因:")
        print("1. API Key 错误或已过期")
        print("2. 余额不足")
        print("3. 网络连接问题")
        print("\n请检查: https://platform.moonshot.cn/console/api-keys")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Kimi API 连接测试")
    print("=" * 60)
    test_connection()
    print("=" * 60)

