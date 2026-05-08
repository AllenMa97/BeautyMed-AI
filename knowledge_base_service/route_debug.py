# 临时测试脚本 - 检查路由是否正确注册
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接测试路由注册
try:
    from main import app
    print("=== 路由注册测试 ===")
    
    # 打印所有路由
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
            print(f"路由: {route.path}")
    
    # 检查特定路由
    test_routes = ["/knowledge", "/add_knowledge", "/edit_knowledge", "/graph"]
    print("\n=== 路由存在性检查 ===")
    for route in test_routes:
        exists = any(route in path for path in routes)
        print(f"{route}: {'存在' if exists else '不存在'}")
        
    print(f"\n总共注册了 {len(routes)} 个路由")
    
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()