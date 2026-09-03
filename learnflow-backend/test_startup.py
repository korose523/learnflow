#!/usr/bin/env python3
"""
测试脚本：验证 FastAPI 应用可以正常启动
用于排查 CloudBase 部署问题
"""

import sys
import os

# 设置测试环境变量（不依赖外部服务）
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

print("🔍 开始测试 FastAPI 应用...")

try:
    print("1. 测试导入 FastAPI...")
    from fastapi import FastAPI
    print("   ✅ FastAPI 导入成功")
    
    print("2. 测试导入应用主模块...")
    # 先切换到应用目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 测试导入 main.py
    import app.main
    print("   ✅ app.main 导入成功")
    
    print("3. 测试 FastAPI 应用实例...")
    app_instance = app.main.app
    print(f"   ✅ FastAPI 应用创建成功: {type(app_instance)}")
    
    print("4. 测试路由加载...")
    routes = [route.path for route in app_instance.routes]
    print(f"   ✅ 已加载 {len(routes)} 个路由")
    for route in routes[:10]:  # 只显示前10个
        print(f"      - {route}")
    
    print("\n" + "="*50)
    print("✅ 应用可以正常导入和初始化！")
    print("="*50)
    
except ImportError as e:
    print(f"\n❌ 导入错误: {e}")
    print("可能的原因：")
    print("  1. requirements.txt 中的依赖未安装")
    print("  2. Python 版本不兼容")
    print("  3. 代码中有语法错误")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ 未知错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n📋 建议的下一步：")
print("  1. 本地运行: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
print("  2. 访问 <INTERNAL_URL_REMOVED>")
print("  3. 如果本地可以运行，再部署到 CloudBase")
