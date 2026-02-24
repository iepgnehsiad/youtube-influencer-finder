#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback
import os
from pathlib import Path

def ensure_output_dir():
    """确保 output 目录存在"""
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Output directory ready: {output_dir.absolute()}")

def main():
    """主程序入口，包含完整的错误处理"""
    try:
        print("=" * 50)
        print("🔍 Pacdora Influencer Scanner Started")
        print("=" * 50)
        
        # 验证 API 密钥
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("❌ YOUTUBE_API_KEY environment variable not set!")
        print("✅ API Key found")
        
        # 确保输出目录存在
        ensure_output_dir()
        
        # 导入依赖
        try:
            import pandas as pd
            from googleapiclient.discovery import build
            print("✅ All dependencies loaded successfully")
        except ImportError as e:
            raise ImportError(f"Failed to import required packages: {e}")
        
        # ========== 这里放您的原始代码 ==========
        # 例如：
        # search_queries = ["AI Tool for Packaging Design", "designfreelancer", "packagetrends"]
        # for query in search_queries:
        #     print(f"🔍 Pacdora 挖掘中: {query}")
        #     # 您的搜索和处理逻辑
        # ========================================
        
        print("=" * 50)
        print("✅ Pacdora scan completed successfully!")
        print("=" * 50)
        return 0
        
    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ ERROR: {type(e).__name__}")
        print("=" * 50)
        print(f"Details: {str(e)}\n")
        traceback.print_exc()
        print("=" * 50)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
