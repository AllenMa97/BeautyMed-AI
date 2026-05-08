#!/usr/bin/env python3
"""
测试路由是否正确注册的脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入应用以检查路由
try:
    from main import app
    print("应用导入成功")
    
    # 打印所有路由
    print("\n=== 所有路由 ===")
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
            print(f"路径: {route.path}")
    
    # 检查特定路由是否存在
    expected_routes = ["/knowledge", "/add_knowledge", "/edit_knowledge", "/graph"]
    print("\n=== 路由检查 ===")
    for route in expected_routes:
        exists = any(route in path for path in routes)
        print(f"{route}: {'✓ 存在' if exists else '✗ 不存在'}")
        
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()