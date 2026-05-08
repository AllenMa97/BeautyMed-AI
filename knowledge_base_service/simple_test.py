# 测试路由是否正确注册
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 直接导入main模块
    import main
    print("应用导入成功")
    
    # 检查路由
    print("检查路由注册情况...")
    
    # 重新导入以确保最新状态
    import importlib
    importlib.reload(main)
    
    print("测试完成")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()