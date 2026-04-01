#!/usr/bin/env python3
"""
调试JSON解析错误问题
重现前端JSON.parse错误场景
"""

import json
import requests
from flask import Flask, jsonify

# 模拟前端JSON解析错误的各种场景
def test_json_parse_scenarios():
    print("🧪 测试JSON解析错误场景")
    print("=" * 50)
    
    # 模拟可能的后端响应
    test_responses = [
        # 正确的JSON响应
        {'status': 'processing', 'current': 10, 'total': 100, 'percentage': 10},
        
        # 可能导致前端JSON.parse错误的响应
        '<html><body>Internal Server Error</body></html>',  # HTML错误页面
        'Internal Server Error',  # 纯文本错误
        '',  # 空响应
        'undefined',  # JavaScript undefined
        'null',  # JSON null
        '{invalid json}',  # 无效JSON
        '500 Internal Server Error',  # HTTP错误信息
        'Connection timeout',  # 连接超时
    ]
    
    for i, response in enumerate(test_responses):
        print(f"\n测试场景 {i+1}:")
        print(f"响应内容: {str(response)[:100]}...")
        
        # 模拟前端 response.json() 调用
        try:
            if isinstance(response, dict):
                # 如果是字典，直接序列化
                json_str = json.dumps(response)
                parsed = json.loads(json_str)
                print("✅ JSON解析成功")
            else:
                # 如果是字符串，尝试解析
                parsed = json.loads(response)
                print("✅ JSON解析成功")
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            print("   这会导致前端的 JSON.parse: unexpected character 错误")
        except Exception as e:
            print(f"❌ 其他错误: {e}")

def test_backend_endpoints():
    """测试后端API端点是否返回正确的JSON"""
    print("\n🔍 测试后端API端点")
    print("=" * 50)
    
    # 模拟后端响应
    app = Flask(__name__)
    
    @app.route('/progress/test')
    def test_progress():
        """正确的JSON响应"""
        return jsonify({
            'status': 'processing',
            'current': 25,
            'total': 100,
            'percentage': 25
        })
    
    @app.route('/progress/error')
    def test_error():
        """错误的响应（可能导致前端JSON解析错误）"""
        # 返回纯文本而不是JSON
        return "Internal Server Error", 500
    
    # 测试正确的端点
    with app.test_client() as client:
        response = client.get('/progress/test')
        print(f"正确端点测试:")
        print(f"  状态码: {response.status_code}")
        print(f"  内容类型: {response.content_type}")
        print(f"  内容: {response.get_data(as_text=True)[:100]}")
        
        # 尝试解析
        try:
            data = response.get_json()
            print("  ✅ 后端返回有效的JSON")
        except:
            print("  ❌ 后端返回无效的JSON")
    
    # 测试错误的端点
    with app.test_client() as client:
        response = client.get('/progress/error')
        print(f"\n错误端点测试:")
        print(f"  状态码: {response.status_code}")
        print(f"  内容类型: {response.content_type}")
        print(f"  内容: {response.get_data(as_text=True)[:100]}")
        
        # 尝试解析
        try:
            data = response.get_json()
            print("  ✅ 后端返回有效的JSON")
        except:
            print("  ❌ 后端返回无效的JSON")
            print("  这会导致前端 JSON.parse 错误")

def analyze_real_issue():
    """分析真实问题的根本原因"""
    print("\n🔧 分析真实问题的根本原因")
    print("=" * 50)
    
    print("可能的原因:")
    print("1. ✅ 后端返回非JSON格式的错误页面")
    print("2. ✅ 网络错误导致响应内容不完整")
    print("3. ✅ 服务器超时返回HTML错误页面")
    print("4. ✅ 内存溢出导致进程崩溃")
    print("5. ✅ 并发处理冲突")
    
    print("\n解决方案:")
    print("1. 🔧 后端确保所有响应都是有效的JSON")
    print("2. 🔧 前端使用安全的JSON解析函数")
    print("3. 🔧 添加适当的错误处理和重试机制")
    print("4. 🔧 实现真正的异步分批处理")
    print("5. 🔧 添加内存使用监控和限制")

def main():
    print("🔍 SRT语音合成工具 - JSON解析错误调试")
    print("=" * 60)
    
    test_json_parse_scenarios()
    test_backend_endpoints()
    analyze_real_issue()
    
    print("\n📋 修复建议:")
    print("1. 确保后端所有路由都返回有效的JSON")
    print("2. 前端使用 response.text() + JSON.parse() 而不是 response.json()")
    print("3. 添加全局错误处理，捕获所有可能的异常")
    print("4. 实现真正的异步处理，避免同步阻塞")

if __name__ == "__main__":
    main()